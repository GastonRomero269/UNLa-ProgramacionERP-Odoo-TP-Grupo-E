from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Propiedades'

    # Otros campos (omitiendo para brevedad)
    name = fields.Char(string="Título", required=True)
    description = fields.Text(string="Descripción")
    postcode = fields.Char(string="Código Postal")
    date_availability = fields.Date(
        string="Fecha disponibilidad",
        copy=False,
        default=lambda self: (datetime.now() + timedelta(days=90)).date()
    )
    expected_price = fields.Float(string="Precio esperado")
    selling_price = fields.Float(string="Precio de venta", copy=False)
    bedrooms = fields.Integer(string="Habitaciones", default=2)
    living_area = fields.Integer(string="Superficie cubierta")
    facades = fields.Integer(string="Fachadas")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Jardín")
    garden_area = fields.Integer(string="Superficie jardín")
    garden_orientation = fields.Selection(
        selection=[
            ('north', 'Norte'),
            ('south', 'Sur'),
            ('east', 'Este'),
            ('west', 'Oeste'),
        ],
        default="north",
        string="Orientación del jardín"
    )
    state = fields.Selection(
        selection=[
            ('new', 'Nuevo'),
            ('offer_received', 'Oferta recibida'),
            ('offer_accepted', 'Oferta aceptada'),
            ('sold', 'Vendido'),
            ('canceled', 'Cancelado'),
        ],
        string="Estado",
        required=True,
        default='new',
        copy=False
    )
    property_type_id = fields.Many2one(
        comodel_name='estate.property.type',
        string="Tipo Propiedad"
    )
    buyer_id = fields.Many2one(
        comodel_name='res.partner',
        string="Comprador"
    )
    salesman_id = fields.Many2one(
        comodel_name='res.users',
        string="Vendedor",
        copy=False,
        default=lambda self: self.env.user
    )
    tag_ids = fields.Many2many(
        comodel_name='estate.property.tag',
        string="Etiquetas"
    )   
    offer_ids = fields.One2many(
        comodel_name='estate.property.offer',
        inverse_name='property_id',
        string="Ofertas"
    )

    total_area = fields.Integer(
        string="Superficie total",
        compute="_compute_total_area",
        store=True
    )
    best_offer = fields.Float(
        string="Mejor oferta",
        compute="_compute_best_offer"
    )

    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        for record in self:
            prices = record.offer_ids.mapped('price')
            record.best_offer = max(prices) if prices else 0.0

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            living_area = record.living_area or 0
            garden_area = record.garden_area or 0
            record.total_area = living_area + garden_area
            
    @api.onchange('garden')
    def _onchange_garden(self):
        """Actualiza garden_area según el estado de garden."""
        if self.garden:
            self.garden_area = 10
        else:
            self.garden_area = 0
    
    @api.onchange('expected_price')
    def _onchange_expected_price(self):
        """Muestra una advertencia si el precio esperado es menor a 10,000."""
        if self.expected_price and self.expected_price < 10000:
            return {
                'warning': {
                    'title': 'Precio Bajo',
                    'message': 'El precio esperado ingresado es menor a 10,000. Verifique si es correcto o si se trata de un error de tipeo.'
                }
            }
            
    def action_cancel(self):
        """Cambia el estado de la propiedad a 'canceled'."""
        for record in self:
            if record.state == 'sold':
                raise UserError("No se puede cancelar una propiedad que ya ha sido vendida.")
            record.state = 'canceled'

    def action_sold(self):
        """Cambia el estado de la propiedad a 'sold'."""
        for record in self:
            if record.state == 'canceled':
                raise UserError("No se puede marcar como vendida una propiedad que ha sido cancelada.")
            record.state = 'sold'
            
    @api.onchange('offer_ids')
    def _onchange_offer_ids(self):
        """Actualiza el estado basado en las ofertas."""
        if self.offer_ids and self.state not in ('sold', 'canceled'):
            self.state = 'offer_received'
        accepted_offers = self.offer_ids.filtered(lambda o: o.status == 'accepted')
        if accepted_offers:
            if len(accepted_offers) > 1:
                raise UserError("Solo una oferta puede ser aceptada. Revisa las ofertas.")
            self.state = 'offer_accepted'
            self.buyer_id = accepted_offers.partner_id
            self.selling_price = accepted_offers.price
            other_offers = self.offer_ids - accepted_offers
            other_offers.write({'status': 'refused'})