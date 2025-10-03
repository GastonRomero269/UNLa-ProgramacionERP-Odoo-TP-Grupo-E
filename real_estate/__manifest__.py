{
    'name': 'Inmobiliaria',
    'author': 'UNLa',
    'version': '1.0.0',
    'description': 'Aplicacion para gestionar venta de propiedades',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/real_estate_res_groups.xml',
        'views/estate_property_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_property_offer_views.xml',
        'views/estate_menu_item_views.xml',
    ],
    'application': True,
}