from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Oferta sobre propiedad'

    price = fields.Float(string="Precio", required=True)
    status = fields.Selection(
        selection=[
            ('accepted', 'Aceptada'),
            ('refused', 'Rechazada')
        ],
        string="Estado"
    )
    partner_id = fields.Many2one(comodel_name='res.partner', string="Ofertante", required=True)
    property_id = fields.Many2one(comodel_name='estate.property', string="Propiedad", required=True)
    validity = fields.Integer(string="Validez (días)", default=7)
    date_deadline = fields.Date(
        string="Fecha límite",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True
    )
    
    property_type_id = fields.Many2one(
        comodel_name='estate.property.type',
        string="Tipo de Propiedad",
        related="property_id.property_type_id",
        store=True
    )

    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                record.date_deadline = record.create_date + timedelta(days=record.validity)
            else:
                record.date_deadline = False

    def _inverse_date_deadline(self):
        for record in self:
            if record.date_deadline and record.create_date:
                delta = record.date_deadline - record.create_date.date()
                record.validity = delta.days
            else:
                record.validity = 7
                
    @api.model
    def create(self, vals):
        """Sobrescribe create para rechazar automáticamente ofertas si la propiedad está vendida o cancelada."""
        property_id = vals.get('property_id')
        if property_id:
            property_record = self.env['estate.property'].browse(property_id)
            if property_record.state in ('sold', 'canceled'):
                vals['status'] = 'refused'
        return super(EstatePropertyOffer, self).create(vals)

    def write(self, vals):
        """Sobrescribe write para rechazar automáticamente ofertas si la propiedad está vendida o cancelada."""
        for offer in self:
            # Usar el nuevo property_id si se está actualizando, o el existente
            property_id = vals.get('property_id', offer.property_id.id)
            property_record = self.env['estate.property'].browse(property_id)
            if property_record.state in ('sold', 'canceled'):
                vals['status'] = 'refused'
        return super(EstatePropertyOffer, self).write(vals)
                
    def action_accept_offer(self):
        """Acepta la oferta, actualiza la propiedad y rechaza otras ofertas."""
        for offer in self:
            # Verificar que la propiedad no esté en estado 'sold' o 'canceled'
            if offer.property_id.state in ('sold', 'canceled'):
                raise UserError("No se puede aceptar una oferta para una propiedad que está vendida o cancelada.")
            # Rechazar otras ofertas de la misma propiedad
            other_offers = offer.property_id.offer_ids - offer
            other_offers.write({'status': 'refused'})
            # Actualizar la oferta actual a 'accepted'
            offer.status = 'accepted'
            # Actualizar la propiedad
            offer.property_id.write({
                'state': 'offer_accepted',
                'buyer_id': offer.partner_id,
                'selling_price': offer.price
            })
                
    @api.onchange('status')
    def _onchange_status(self):
        """Actualiza el estado de la propiedad a 'offer_accepted' si la oferta es aceptada."""
        for offer in self:
            if offer.status == 'accepted':
                # Verificar que la propiedad no esté en estado 'sold' o 'canceled'
                if offer.property_id.state in ('sold', 'canceled'):
                    raise UserError("No se puede aceptar una oferta para una propiedad que está vendida o cancelada.")
                # Rechazar otras ofertas de la misma propiedad
                other_offers = offer.property_id.offer_ids - offer
                other_offers.write({'status': 'refused'})
                # Cambiar el estado de la propiedad a 'offer_accepted'
                offer.property_id.state = 'offer_accepted'