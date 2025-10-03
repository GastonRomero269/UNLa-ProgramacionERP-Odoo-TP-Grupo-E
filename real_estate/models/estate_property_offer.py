from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Oferta sobre propiedad'

    price = fields.Float(string="Precio", required=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Ofertante", required=True)
    property_id = fields.Many2one(comodel_name='estate.property', string="Propiedad", required=True)
    validity = fields.Integer(string="Validez (días)", default=7)
    
    # Solo se podra aceptar propiedades que no esten vendidas o canceladas
    status = fields.Selection(
        selection=[
            ('accepted', 'Aceptada'),
            ('refused', 'Rechazada')
        ],
        string="Estado"
    )
    
    # Fecha limite calculada a partir de la fecha de creacion + validez
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

    # Inverso para actualizar la validez si se cambia la fecha límite
    def _inverse_date_deadline(self):
        for record in self:
            if record.date_deadline and record.create_date:
                delta = record.date_deadline - record.create_date.date()
                record.validity = delta.days
            else:
                record.validity = 7

    # Marcar como rechazado si la propiedad está vendida o cancelada al actualizar la oferta
    def write(self, vals):
        for offer in self:
            property_id = vals.get('property_id', offer.property_id.id)
            property_record = self.env['estate.property'].browse(property_id)
            if property_record.state in ('sold', 'canceled'):
                vals['status'] = 'refused'
        return super(EstatePropertyOffer, self).write(vals)
    
    # Aceptar la oferta y marcar las otras como rechazadas
    def action_accept_offer(self):
        for offer in self:
            if offer.property_id.state in ('sold', 'canceled'):
                raise UserError("No se puede aceptar una oferta para una propiedad que está vendida o cancelada.")
            other_offers = offer.property_id.offer_ids - offer
            other_offers.write({'status': 'refused'})
            offer.status = 'accepted'
            offer.property_id.write({
                'state': 'offer_accepted',
                'buyer_id': offer.partner_id,
                'selling_price': offer.price
            })
                
    # Segun la fecha de creacion y su validez se calcula la fecha límite
    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                record.date_deadline = record.create_date + timedelta(days=record.validity)
            else:
                record.date_deadline = False

    # Se marca como rechazado si la propiedad está vendida o cancelada al crear la oferta
    @api.model
    def create(self, vals):
        property_id = vals.get('property_id')
        if property_id:
            property_record = self.env['estate.property'].browse(property_id)
            if property_record.state in ('sold', 'canceled'):
                vals['status'] = 'refused'
        return super(EstatePropertyOffer, self).create(vals)            
    
    
    # Se verifica que la propiedad no haya sido vendida o cancelada al cambiar el estado de la oferta         
    @api.onchange('status')
    def _onchange_status(self):
        for offer in self:
            if offer.status == 'accepted':
                if offer.property_id.state in ('sold', 'canceled'):
                    raise UserError("No se puede aceptar una oferta para una propiedad que está vendida o cancelada.")
                other_offers = offer.property_id.offer_ids - offer
                other_offers.write({'status': 'refused'})
                offer.property_id.state = 'offer_accepted'