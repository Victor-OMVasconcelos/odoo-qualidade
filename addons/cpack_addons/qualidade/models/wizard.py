from odoo import models, fields, api, exceptions, _

class Wizard_indeferido(models.TransientModel):
    _name = 'wizard.indeferido'

    
    motivo = fields.Text(string="Motivo do indeferimento", required=True)
    responsavel = fields.Char(string='Responsavel', default=lambda self: str(self.env.user.name), required=True)

    def action_confirm(self):
        active_id = self._context.get('active_id')
        solicitacao = self.env['qualidade.solicitacao'].browse(active_id)

        if solicitacao:
            solicitacao.write({
                'situacao': 'indeferido',
                'motivo': self.motivo,
            })

            if solicitacao.source_id:
                solicitacao.source_id.write({
                    'situacao': 'indeferido',
                    'motivo': self.motivo,
                    'responsavel': self.responsavel,
                })
            solicitacao.unlink()

        return self.env.ref('qualidade.acao_solicitacao').read()[0]
    
class SolicitarWizard(models.TransientModel):
    _name = 'qualidade.solicitar.wizard'
    _description = 'Solicitar mudanças no arquivo'

    processo = fields.Selection([('extrusao', 'Extrusão')] ,string = "Processos", required = True)
    arquivo_id = fields.Many2one('visualizar.arquivo', string="Arquivo Original", required=True)
    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção", required = True, default="1")
    diametro = fields.Selection([('19','Diâmetro: 19'),('22','Diâmetro: 22'),('25','Diâmetro: 25'),('30','Diâmetro: 30'),('35','Diâmetro: 35'),('40','Diâmetro: 40'),('50','Diâmetro: 50'),('60','Diâmetro: 60')], string = "Diâmetro", required = True)
    data = fields.Date(string="Data", required=True,default=fields.Date.today())
    solicitante = fields.Char(string='Solicitante', default=lambda self: str(self.env.user.name), required=True)
    parame_alterado = fields.Char(string="Parâmetro alterado (incluir código)", required=True)
    valor_novo = fields.Char(string="Novo valor", required=True)
    motivo = fields.Text(string="Motivo",required=True)
    situacao = fields.Selection([('aguardando','Aguardando'),('avaliando','Avaliando'),('deferido','Deferido'),('indeferido','Indeferido')],string="Situacao", tracking=True,copy=False,default='aguardando')
  
    @api.model
    def default_get(self, fields_list):
        res = super(SolicitarWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            record = self.env['visualizar.arquivo'].browse(active_id)
            res.update({
                'arquivo_id': record.id,
                'processo': record.processo,
                'linha_producao': record.linha_producao,
                'diametro': record.diametro,  
            })
        return res

    def enviar_para_analise(self):
        for r in self:
            criado = self.env['qualidade.solicitar'].create({
                'processo': r.processo,
                'linha_producao': r.linha_producao,
                'diametro': r.diametro, 
                'data': r.data,
                'solicitante': r.solicitante,
                'parame_alterado': r.parame_alterado,
                'valor_novo': r.valor_novo,
                'motivo': r.motivo,
                'situacao': 'avaliando',
            })

            self.env['qualidade.solicitacao'].create({
                'linha_producao': r.linha_producao,
                'data': r.data,
                'solicitante': r.solicitante,
                'parame_alterado': r.parame_alterado,
                'valor_novo': r.valor_novo,
                'motivo': r.motivo,
                'situacao': 'avaliando',
                'source_id': criado.id
            })
            
            
            return self.env.ref('qualidade.acao_visualizar').read()[0]
