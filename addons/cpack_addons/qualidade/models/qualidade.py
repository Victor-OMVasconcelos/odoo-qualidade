from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from odoo.tools import human_size
from datetime import timedelta
import base64
import logging

_logger = logging.getLogger(__name__)

class Gerenciar(models.Model):
    _name = 'qualidade.gerenciar'
    _description = 'Gerenciador de arquivos'

    processo = fields.Selection([('extrusao', 'Extrusão')] ,string = "Processos", required = True)
    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção", required = True)
    diametro = fields.Selection([('19','Diâmetro: 19'),('22','Diâmetro: 22'),('25','Diâmetro: 25'),('30','Diâmetro: 30'),('35','Diâmetro: 35'),('40','Diâmetro: 40'),('50','Diâmetro: 50'),('60','Diâmetro: 60')], string = "Diâmetro", required = True)
    arquivo = fields.Binary(string = "Arquivo", attachment = True, store = True, max_width=1920, max_height=1920)
    estagio = fields.Selection([('rascunho','Rascunho'),('revisao','Revisao'),('publicado','Publicado')], string = "Estágio", tracking=True,copy=False,default='rascunho')
    color = fields.Integer()



    @api.model
    def create(self,vals):
        record = super(Gerenciar, self).create(vals)

        formatted_mudancas = {}
        for field, value in vals.items():
            field_type = self._fields[field].type
    
            if field_type == 'binary':
                formatted_mudancas[field] = f"Binary File (size: {human_size(len(value))})" if value else "No File"
    
            elif field_type == 'many2one':  
                related_record = self.env[self._fields[field].comodel_name].browse(value)
                formatted_mudancas[field] = related_record.display_name if related_record.exists() else "Unknown Record"
    
            else:  
                formatted_mudancas[field] = value


        mudancas_str = ", ".join(f"{key}: {val}" for key, val in formatted_mudancas.items())


        self.env['record.mudar.log'].create({
            'model_name': self._name,
            'record_id': record.id,
            'action_type': 'criar',
            'user_id': self.env.user.id,
            'mudancas': mudancas_str,
        })

        

        return record
    
    def write(self, vals):
        res = super(Gerenciar, self).write(vals)
        for rec in self:
            formatted_mudancas = {}
            for field, value in vals.items():
                field_type = self._fields[field].type
    
                if field_type == 'binary':
                    formatted_mudancas[field] = f"Binary File (size: {human_size(len(value))})" if value else "No File"
    
                elif field_type == 'many2one':  
                    related_record = self.env[self._fields[field].comodel_name].browse(value)
                    formatted_mudancas[field] = related_record.display_name if related_record.exists() else "Unknown Record"
    
                else:  
                    formatted_mudancas[field] = value


        mudancas_str = ", ".join(f"{key}: {val}" for key, val in formatted_mudancas.items())


        self.env['record.mudar.log'].create({
            'model_name': self._name,
            'record_id': rec.id,
            'action_type': 'alterar',
            'user_id': self.env.user.id,
            'mudancas': mudancas_str,
        })


        if vals.get('estagio') == 'publicado' or rec.estagio == 'publicado':
            mirror_vals = {
                'processo': rec.processo,
                'linha_producao': rec.linha_producao,
                'diametro': rec.diametro,
                'arquivo': rec.arquivo,
                'estagio': 'publicado',
            }
            mirror = self.env['visualizar.arquivo'].search([('source_id', '=', rec.id)], limit=1)
            if mirror:
                mirror.write(mirror_vals)
            else:
                    mirror_vals['source_id'] = rec.id
                    self.env['visualizar.arquivo'].create(mirror_vals)
        return res

    
    def abrir_todos_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log de mudancas',
            'res_model': 'record.mudar.log',
            'view_mode': 'list,form',
            'domain': [('model_name', '=', self._name), ('record_id', 'in', self.ids )],
            'target': 'current', 
        }
    
    def revisar(self):
        for r in self:
            if r.estagio == 'rascunho':
                r.write({'estagio': 'revisao'})

    def publicar(self):
        for r in self:
            r.write({'estagio': 'publicado'})
            
class VisualizarArquivos(models.Model):
    _name = 'visualizar.arquivo'

    processo = fields.Selection([('extrusao', 'Extrusão')] ,string = "Processos", required = True)
    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção", required = True)
    diametro = fields.Selection([('19','Diâmetro: 19'),('22','Diâmetro: 22'),('25','Diâmetro: 25'),('30','Diâmetro: 30'),('35','Diâmetro: 35'),('40','Diâmetro: 40'),('50','Diâmetro: 50'),('60','Diâmetro: 60')], string = "Diâmetro", required = True)
    arquivo = fields.Binary(string = "Arquivo", attachment = True, store = True, max_width=1920, max_height=1920)
    source_id = fields.Many2one('qualidade.gerenciar', string='Formulario original')
    estagio = fields.Selection([('publicado','Publicado')], string = "Estágio",default='publicado')

    def solicitar_alteracao(self):
        for r in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Solicitação',
                'res_model': 'qualidade.solicitar.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': r.id} 
            }
   
class Solicitar(models.Model):
    _name = 'qualidade.solicitar'
    _description = 'Solicitar mudanças no arquivo'

    diametro = fields.Selection([('19','Diâmetro: 19'),('22','Diâmetro: 22'),('25','Diâmetro: 25'),('30','Diâmetro: 30'),('35','Diâmetro: 35'),('40','Diâmetro: 40'),('50','Diâmetro: 50'),('60','Diâmetro: 60')], string = "Diâmetro", required = True)
    processo = fields.Selection([('extrusao', 'Extrusão')] ,string = "Processos", required = True)
    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção", required = True)
    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção", required = True, default="1")
    data = fields.Date(string="Data", required=True,default=fields.Date.today())
    solicitante = fields.Char(string='Solicitante', default=lambda self: str(self.env.user.name), required=True)
    parame_alterado = fields.Char(string="Parâmetro alterado (incluir código)", required=True)
    valor_novo = fields.Char(string="Novo valor", required=True)
    motivo = fields.Text(string="Motivo",required=True)
    situacao = fields.Selection([('aguardando','Aguardando'),('avaliando','Avaliando'),('deferido','Deferido'),('indeferido','Indeferido')],string="Situacao", tracking=True,copy=False,default='aguardando')
    editavel = fields.Integer(string="Editavel", compute="_procurar_editavel")
    responsavel = fields.Char(string='Responsavel')


            

    def deletar_auto(self):
        for r in self:
            date_created = r.data
            if fields.Date.today() >= (date_created + timedelta(days=7)):
                r.unlink()

    def create_cron_job(self):
        self.env.ref('qualidade.deletar_auto_cron').write({
            'active': True
        })
class Solicitacoes(models.Model):
    _name = 'qualidade.solicitacao'

    linha_producao = fields.Selection([('1','Linha 1'),('2','Linha 2'),('3','Linha 3'),('4','Linha 4'),('5','Linha 5'),('6','Linha 6')], string = "Linha de produção")
    data = fields.Date(string="Data")
    solicitante = fields.Char(string='Solicitante')
    parame_alterado = fields.Char(string="Parâmetro alterado (incluir código)")
    valor_novo = fields.Char(string="Novo valor")
    motivo = fields.Text(string="Motivo")
    situacao = fields.Selection([('avaliando','Avaliando'),('deferido','Deferido'),('indeferido','Indeferido')],string="Situacao")
    source_id = fields.Many2one('qualidade.solicitar', string='Solicitacao original')
    responsavel = fields.Char(string='Responsavel', default=lambda self: str(self.env.user.name), required=True)

   
    def solicitacao_deferido(self):
        for r in self:
            r.situacao = 'deferido'
            r.motivo = 'Deferido'
            if r.source_id:
                r.source_id.situacao = 'deferido'
                r.source_id.motivo = 'Deferido'
                r.source_id.responsavel = r.responsavel
            r.unlink()
        return self.env.ref('qualidade.acao_solicitacao').read()[0]

    def solicitacao_indeferido(self):
        for r in self:
            r.situacao = 'indeferido'
            if r.source_id:
                r.source_id.situacao = 'indeferido'
            return {
                'type': 'ir.actions.act_window',
                'name': 'Indeferir',
                'res_model': 'wizard.indeferido',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': r.id} 
            }
        
class RecordMudarLog(models.Model):
    _name = 'record.mudar.log'

    model_name = fields.Char('Nome do modelo')
    record_id = fields.Integer('Record id')
    action_type = fields.Selection([('criar','Criar'),('alterar','Alterar')], string="Ação")
    user_id = fields.Many2one('res.users', string = 'Usuário responsável')
    data_mudancas = fields.Datetime('Data da mudança', default=fields.Datetime.now)
    mudancas = fields.Text('Mudanças')


    def action_back_to_gerenciar(self):
        action = self.env.ref('qualidade.acao_gerenciador').read()[0]
        return action