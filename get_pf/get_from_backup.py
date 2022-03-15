# Загружаем всю информацию (+ таблицы для совместимости) из АПИ ПФ

import json
import os
import requests
import xmltodict
from lxml import etree, objectify

from lib import format_phone
from hide_data import OFFICETOWNS, DEPARTMENTS, URL, USR_Tocken, PSR_Tocken, PF_ACCOUNT

PF_BACKUP_DIRECTORY = 'planfix-data-202202182037'
PF_HEADER = {"Accept": 'application/xml', "Content-Type": 'application/xml'}
RELOAD_ALL_FROM_API = False

def create_record(id, model, sources):
    """Создаем запись БД flectra"""
    record = objectify.Element('record', id=id, model=model)
    fields = []
    i = -1
    for source in sources:
        i += 1
        if str(source).endswith('_id'):
            fields.append(objectify.SubElement(record, 'field', name=source, ref=sources[source]))
        elif source and sources[source]:
            fields.append(objectify.SubElement(record, 'field', name=source))
            fields[i]._setText(sources[source])
        else:
            print(id, source, sources[source])
    return record


def load_users_from_api():
    """Загрузка всех юзеров ПФ из АПИ в файл users.xml"""
    xml_string = ''
    i = 1
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="user.getList"><account>' + PF_ACCOUNT +
                 '</account><pageSize>100</pageSize><pageCurrent>' +
                 str(i) + '</pageCurrent></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            xml_string += str(answer.text).replace('<response status="ok">', '').replace('</response>', '') \
                .replace('<?xml version="1.0" encoding="UTF-8"?>', '').replace('</users>', '')
        i += 1
    while xml_string.find('<users totalCount=') > -1:
        xml_string = xml_string[:xml_string.find('<users totalCount=')] + \
                     xml_string[xml_string.find('>', xml_string.find('<users totalCount=')) + 1:]
    try:
        with open(os.path.join(PF_BACKUP_DIRECTORY, 'users.xml'), 'w') as xml_writer:
            xml_writer.write('<?xml version="1.0" encoding="UTF-8"?>\n<users>\n' + xml_string + '\n</users>')
    except IOError:
        pass


def load_contacts_from_api():
    """Загрузка всех контактов Сотрудников (группа №6532326) из АПИ ПФ в файл contacts.xml"""
    xml_string = ''
    i = 1
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="contact.getList"><account>' + PF_ACCOUNT +
                 '</account><pageCurrent>' + str(i) +
                 '</pageCurrent><pageSize>100</pageSize><target>6532326</target></request>' ,
            auth=(USR_Tocken, PSR_Tocken))
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            xml_string += str(answer.text).replace('<response status="ok">','').replace('</response>','')\
                .replace('<?xml version="1.0" encoding="UTF-8"?>','').replace('</contacts>','')
        i += 1
    while xml_string.find('<contacts totalCount=') > -1:
        xml_string = xml_string[:xml_string.find('<contacts totalCount=')] + \
                     xml_string[xml_string.find('>',xml_string.find('<contacts totalCount=')) + 1:]
    try:
        with open(os.path.join(PF_BACKUP_DIRECTORY, 'contacts.xml'), 'w') as xml_writer:
            xml_writer.write('<?xml version="1.0" encoding="UTF-8"?>\n<contacts>\n' + xml_string + '\n</contacts>')
    except IOError:
        pass

def load_group_names_from_api():
    """ Загружаем из АПИ ПФ названия групп от id """
    groups_id2names = {}
    i = 1
    while True:
        answer = requests.post(
            URL,
            headers=PF_HEADER,
            data='<request method="userGroup.getList"><account>' + PF_ACCOUNT
                 + '</account><pageSize>100</pageSize><pageCurrent>' + str(i) + '</pageCurrent></request>',
            auth=(USR_Tocken, PSR_Tocken)
        )
        if answer.text.find('count="0"/></response>') > -1:
            break
        else:
            groups = xmltodict.parse(answer.text)['response']['userGroups']['userGroup']
            for group in groups:
               groups_id2names[group['id']] = group['name']
        i += 1
    return groups_id2names


if __name__ == "__main__":
    # Если задано - обновляем данные из АПИ
    if RELOAD_ALL_FROM_API:
        load_contacts_from_api()
        load_users_from_api()

    # Загружаем список групп
    groups_id2names = load_group_names_from_api()

    # Загружаем данные сотрудников из .xml юзеров
    users_xml = ''
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'users.xml'), 'r') as file_handler:
        for line in file_handler:
            users_xml += line
    users_dict = xmltodict.parse(users_xml)
    users_db = {}
    employees = {}
    # Переводим в формат users_db[email], заполняем БД слияния контактов и юзеров employees[e-mail]
    for user in users_dict['users']['user']:
        if user.get('email', None):
            users_db[user['email']] = user
            employees[user['email']] = {'name': str(user['lastName']) + ' ' + str(user['name']) + ' '
                                                + str(user['midName'])}
            employees[user['email']]['work_email'] = user['email']
            if user.get('phones', None):
                if user['phones']:
                    if str(type(user['phones']['phone'])).find('list') > -1:
                        employees[user['email']]['mobile_phone'] = \
                            str(format_phone(user['phones']['phone'][0]['number']))
                    else:
                        employees[user['email']]['mobile_phone'] = str(format_phone(user['phones']['phone']['number']))
            if user.get('sex', None):
                employees[user['email']]['gender'] = str(user['sex']).lower()
            if user.get('id', None):
                employees[user['email']]['id_pf'] = str(user['id'])
            if user.get('general', None):
                employees[user['email']]['general_user_pf'] = str(user['general'])
            if user.get('active', None):
                employees[user['email']]['active'] = str(user['status'] == 'ACTIVE')
        else:
            print(str(user['id']), str(user['lastName']), str(user['name']), str(user['midName']), ' - нет e-mail')

    # Загружаем данные сотрудников из .xml контактов
    contacts_xml = ''
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'contacts.xml'), 'r') as file_handler:
        for line in file_handler:
            contacts_xml += line
    contacts_dict = xmltodict.parse(contacts_xml)
    contacts_db = {}
    # Переводим в формат users_db[email], заполняем БД сляния контактов и юзеров employees[e-mail]
    for contact in contacts_dict['contacts']['contact']:
        email = ''
        for field in contact['customData']['customValue']:
            if field['field']['name'] == 'Корпоративная почта':
                email = field['text']
        if email:
            contacts_db[email] = contact
            if not employees.get(email, None):
                employees[email] = {}
            employees[email]['work_email'] = email
            employees[email]['general_contact_pf'] = contact['general']
            employees[email]['userid_pf'] = contact['userid']
            for field in contact['customData']['customValue']:
                if field['field']['name'] == 'ФИО' and employees[email].get('name', '').find('None') == -1:
                    employees[email]['name'] = field['text']
                if field['field']['name'] == 'Статус':
                    employees[email]['status'] = field['text']
                if field['field']['name'] == 'Подразделение (отдел)' and field['text']:
                    if field['text'] == 'ПродБлок':
                        field['text'] = 'Продуктовый блок'
                    employees[email]['department_id'] = 'department_' +  str(DEPARTMENTS.index(str(field['text'])))
        else:
            print(str(contact['id']), str(contact['general']), ' - нет e-mail')

    # Заголовок xml
    flectra_root = objectify.Element('flectra')
    flectra_data = objectify.SubElement(flectra_root, 'data')

    # Базовые департаменты, ГД, ЗГД
    record = create_record('department_gd', 'hr.department', {'name': 'Генеральный директор'})
    flectra_data.append(record)
    record = create_record('department_zgd', 'hr.department', {
        'name': 'Заместитель генерального директора',
        'parent_id': 'department_gd',
    })
    flectra_data.append(record)
    for i, department in enumerate(DEPARTMENTS):  # DEPARTMENTS - list с именами департаментов
        record = create_record('department_' + str(i), 'hr.department', {
            'name': department,
            'parent_id': 'department_zgd',
        })
        flectra_data.append(record)

    # Спарвочник офисов-городов
    for i, officetown in enumerate(OFFICETOWNS):   # OFFICETOWNS - list с именами офисегородов
        record = create_record('officetown_' + str(i), 'hr_pf.officetown', {'name': officetown})
        flectra_data.append(record)


    for i, employe in enumerate(employees):
        record = create_record(employe.replace('.','-'), 'hr.employee', employees[employe])
        flectra_data.append(record)

    # удаляем все lxml аннотации.
    objectify.deannotate(flectra_root)
    etree.cleanup_namespaces(flectra_root)

    # конвертируем все в привычную нам xml структуру.
    obj_xml = etree.tostring(flectra_root,
                             pretty_print=True,
                             xml_declaration=True,
                             encoding='UTF-8'
                             )

    try:
        with open("../data/hr_pf_data.xml", "wb") as xml_writer:
            xml_writer.write(obj_xml)
    except IOError:
        pass
