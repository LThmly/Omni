"""One-way migration from the four original templates to component apps."""
import copy
from .runtime import validate_app


def to_composed(app):
    if app.get('module')=='composed':return copy.deepcopy(validate_app(app))
    result={'id':app['id'],'module':'composed','title':app['title'][:48],'state':{'fields':[]},'components':[],'actions':[]}
    state=app['state'];kind=app['module']
    def field(id,type,value,**kw):result['state']['fields'].append(dict(id=id,type=type,value=value,**kw))
    def component(id,type,**kw):result['components'].append(dict(id=id,type=type,**kw))
    def action(id,type,target,**kw):result['actions'].append(dict(id=id,action=type,target=target,**kw))
    if kind=='checklist':
        field('items','items',[dict(id='item_'+str(i),label=item['label'],checked=item['checked']) for i,item in enumerate(state['items'])])
        field('entry','text','')
        component('items_view','list',label='Items',bind='items')
        component('entry_input','input',label='New item',bind='entry')
        action('append_item','append','items',source='entry');component('add_button','button',label='Add item',action='append_item')
        action('remove_done','remove_checked','items');component('clear_button','button',label='Remove checked',action='remove_done')
    elif kind=='scoreboard':
        for index,side in enumerate(state['sides'][:2]):
            id='score_'+str(index);field(id,'number',side['score'],min=0,max=1000000)
            component(id+'_view','number',label=side['name'],bind=id,unit='')
            for suffix,amount,label in [('up',1,'+1'),('down',-1,'−1')]:
                aid=id+'_'+suffix;action(aid,'increment',id,amount=amount)
                component(aid+'_button','button',label=side['name']+' '+label,action=aid)
    elif kind=='progress':
        field('value','number',state['value'],min=0,max=state['goal'])
        component('progress_view','progress',label=state['label'],bind='value',goal=state['goal'],unit=state['unit'])
        action('increase','increment','value',amount=state['step'])
        component('add_button','button',label='Add '+str(state['step'])+' '+state['unit'],action='increase')
    elif kind=='key_value':
        for index,row in enumerate(state['rows'][:24]):
            component('row_'+str(index),'text',text=(row['label']+': '+row['value'])[:300],bind=None)
    else:raise ValueError('Unknown legacy module')
    return validate_app(result)
