from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Propiedades'

    name = fields.Char(string="Título", required=True)
    description = fields.Text(string="Descripción")
    postcode = fields.Char(string="Código Postal")
    expected_price = fields.Float(string="Precio esperado")
    selling_price = fields.Float(string="Precio de venta", copy=False)
    bedrooms = fields.Integer(string="Habitaciones", default=2)
    living_area = fields.Integer(string="Superficie cubierta")
    facades = fields.Integer(string="Fachadas")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Jardín")
    garden_area = fields.Integer(string="Superficie jardín", readonly=True)
    
    date_availability = fields.Date(
        string="Fecha disponibilidad",
        copy=False,
        default=lambda self: (datetime.now() + timedelta(days=90)).date()
    )
    
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
    
    # No es seleccionable, se ajusta dinamicamente
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

    # Superficie total, suma de cubierta y jardín
    total_area = fields.Integer(
        string="Superficie total",
        compute="_compute_total_area",
        store=True
    )
    
    # Oferta con el mejor precio
    best_offer = fields.Float(
        string="Mejor oferta",
        compute="_compute_best_offer"
    )
            
    # Acciones para cancelar la propiedad
    def action_cancel(self):
        for record in self:
            if record.state == 'sold':
                raise UserError("No se puede cancelar una propiedad que ya ha sido vendida.")
            record.state = 'canceled'

    # Acciones para vender la propiedad
    def action_sold(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError("No se puede marcar como vendida una propiedad que ha sido cancelada.")
            record.state = 'sold'
    
    # Calcula la mejor oferta
    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        for record in self:
            prices = record.offer_ids.mapped('price')
            record.best_offer = max(prices) if prices else 0.0

    # Calcula la superficie total, suma de cubierta y jardín
    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            garden_area = record.garden_area or 0
            living_area = record.living_area or 0
            record.total_area = living_area + garden_area        
    
    # Limita el área del jardín a 0 si no hay jardín y a 10 si hay jardín
    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
        else:
            self.garden_area = 0
    
    # Si el precio esperado es menor a 10.000 da una advertencia
    @api.onchange('expected_price')
    def _onchange_expected_price(self):
        if self.expected_price and self.expected_price < 10000:
            return {
                'warning': {
                    'title': 'Precio por debajo del minimo',
                    'message': 'El precio esperado ingresado es menor a 10,000 $. Verifique si ingresó la cifra correcta o si se trata de un error de tipeo.'
                }
            }
            
    # Si hay ofertas y la propiedad no está vendida o cancelada, el estado cambia a 'oferta recibida'
    @api.onchange('offer_ids')
    def _onchange_offer_ids(self):
        if self.offer_ids and self.state not in ('sold', 'canceled'):
            self.state = 'offer_received'
        accepted_offers = self.offer_ids.filtered(lambda o: o.status == 'accepted')
        if accepted_offers:
            if len(accepted_offers) > 1:
                raise UserError("Solo se puede aceptar una oferta. Revisa las ofertas.")
            self.state = 'offer_accepted'
            self.selling_price = accepted_offers.price
            self.buyer_id = accepted_offers.partner_id
            other_offers = self.offer_ids - accepted_offers
            other_offers.write({'status': 'refused'})