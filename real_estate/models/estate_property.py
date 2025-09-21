from odoo import models, fields
from datetime import datetime, timedelta

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Propiedades'

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