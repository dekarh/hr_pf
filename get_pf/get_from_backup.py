# Загружаем всю информацию (+ таблицы для совместимости) из АПИ ПФ

import json
import os
import requests
import csv
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
    groups_id2members = {}
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
                groups_id2members[group['id']] = []
        i += 1
    return groups_id2names, groups_id2members


if __name__ == "__main__":
    # Если задано - обновляем данные из АПИ
    if RELOAD_ALL_FROM_API:
        load_contacts_from_api()
        load_users_from_api()

    # Загружаем список групп и пустой список членов для каждой группы
    groups_id2names, groups_id2members = load_group_names_from_api()

    # Загружаем данные сотрудников из .xml юзеров
    users_xml = ''
    with open(os.path.join(PF_BACKUP_DIRECTORY, 'users.xml'), 'r') as file_handler:
        for line in file_handler:
            users_xml += line
    users_dict = xmltodict.parse(users_xml)
    users_db = {}
    employees = {}
    users = {}
    users2groups = {}
    # Переводим в формат users_db[email], заполняем БД слияния контактов и юзеров employees[e-mail] и users[e-mail]
    for user in users_dict['users']['user']:
        if user.get('email', None):
            users_db[user['email']] = user
            if user['midName']:
                employees[user['email']] = {'name': str(user['lastName']) + ' ' + str(user['name']) + ' '
                                                    + str(user['midName'])}
                users[user['email']] = {'name': str(user['lastName']) + ' ' + str(user['name']) + ' '
                                                    + str(user['midName'])}
                users2groups[user['email']] = set()
            else:
                employees[user['email']] = {'name': str(user['lastName']) + ' ' + str(user['name'])}
                users[user['email']] = {'name': str(user['lastName']) + ' ' + str(user['name'])}
                users2groups[user['email']] = set()
            users[user['email']]['login'] = user['email']
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
                users[user['email']]['id_pf'] = str(user['id'])
            if user.get('general', None):
                users[user['email']]['general_user_pf'] = str(user['general'])
            if user.get('active', None):
                users[user['email']]['active'] = str(user['status'] == 'ACTIVE')
            if user.get('userGroups', None):
                if str(type(user['userGroups']['userGroup'])).find('list') > -1:
                    for group in user['userGroups']['userGroup']:
                        groups_id2members[group['id']] += [user['email']]
                        users2groups[user['email']].add(group['id'])
                else:
                    groups_id2members[user['userGroups']['userGroup']['id']] += [user['email']]
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
                users[email] = {'login': email}
                employees[email]['work_email'] = email
            users[email]['general_contact_pf'] = contact['general']
            users[email]['userid_pf'] = contact['userid']
            for field in contact['customData']['customValue']:
                if field['field']['name'] == 'ФИО':
                    if employees[email].get('name', None):
                        if len(str(field['text']).strip().split(' ')) > \
                              len(str(employees[email]['name']).strip().split(' ')):
                            employees[email]['name'] = field['text']
                            users[email]['name'] = field['text']
                    else:
                        employees[email]['name'] = field['text']
                        users[email]['name'] = field['text']
                #if field['field']['name'] == 'Город':
                #if field['field']['name'] == 'д/р сотрудника':
                if field['field']['name'] == 'Статус':
                    employees[email]['status'] = field['text']
                    users[email]['active'] = str(field['text'] == 'Активный')
                    employees[email]['active'] = str(field['text'] == 'Активный')
                if field['field']['name'] == 'Подразделение (отдел)' and field['text']:
                    if field['text'] == 'ПродБлок':
                        field['text'] = 'Продуктовый блок'
                    employees[email]['department_id'] = 'department_' +  str(DEPARTMENTS.index(str(field['text'])))
        else:
            print(str(contact['id']), str(contact['general']), ' - нет e-mail')

    i = 1
    users4employees = {}
    for user in users:
        if users[user].get('id_pf', None):
            users[user]['id'] = 'user_' + users[user]['id_pf']
        elif users[user].get('userid_pf', None):
            users[user]['id'] = 'user_' + users[user]['userid_pf']
        else:
            users[user]['id'] = 'user_' + str(i)
            i += 1
        if users2groups.get(user, None):
            if len(users2groups[user]):
                users[user]['groups_id'] = ''
                for group in users2groups[user]:
                    users[user]['groups_id'] += 'hr_pf.' + group + ','
                users[user]['groups_id'] = users[user]['groups_id'].strip(',')

    i = 1
    sotrudniki = {}
    for employee in employees:
        if users.get(employee, None):
            if users[employee].get('id_pf', None):
                sotrudniki['empl_' + users[employee]['id_pf']] = employees[employee]
                sotrudniki['empl_' + users[employee]['id_pf']]['id_pf'] = users[employee]['id_pf']
            elif users[employee].get('userid_pf', None):
                sotrudniki['empl_' + users[employee]['userid_pf']] = employees[employee]
                sotrudniki['empl_' + users[employee]['userid_pf']]['id_pf'] = users[employee]['userid_pf']
            else:
                sotrudniki['empl_' + str(i)] = employees[employee]
                sotrudniki['empl_' + str(i)]['id_pf'] = str(i)
                i += 1

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

    # Справочник офисов-городов
    for i, officetown in enumerate(OFFICETOWNS):   # OFFICETOWNS - list с именами офисегородов
        record = create_record('officetown_' + str(i), 'hr_pf.officetown', {'name': officetown})
        flectra_data.append(record)

    # Группы доступа, сначала корневая группа "Планфикс" в .xml
    record = create_record('category_pf', 'ir.module.category', {'name': 'ПланФикс'})
    flectra_data.append(record)
    for groups_id2name in groups_id2names:
        record = create_record(groups_id2name, 'res.groups',{'name': groups_id2names[groups_id2name],
                                                             'category_id': 'category_pf',
                                                             'id_from_pf': str(groups_id2name)})
        flectra_data.append(record)

    # Юзеры в .csv
    with open('../data/users.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['id', 'name', 'login', 'active', 'id_pf',
                                                     'general_user_pf', 'general_contact_pf', 'userid_pf', 'groups_id'])
        writer.writeheader()
        for user in users:
            writer.writerow(users[user])

    #for i, user in enumerate(users):
    #    record = create_record(user.replace('.','_'), 'res.users', users[user])
    #    flectra_data.append(record)

    # Сотрудники в .xml
    for sotrudnik in sotrudniki:
        record = create_record(sotrudnik, 'hr.employee', sotrudniki[sotrudnik])
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
