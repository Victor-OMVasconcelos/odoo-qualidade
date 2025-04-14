{
    'name': "Qualidade",
    'version': '1.0.0',
    'depends': ['base'],
    'installable': True,
    'author': "Qualidade, C-pack",
    'category': 'Repair',
    'description': """
    Um modulo para qualidade testar e implementar operações.
    """,
    
    'assets' : {
        'web.assets_backend' :[
            'qualidade/static/src/css/style.css',
        ]
    },

    'data': [
        'views/qualidade.xml',
    ],
    
    'demo': [
        
    ],
}