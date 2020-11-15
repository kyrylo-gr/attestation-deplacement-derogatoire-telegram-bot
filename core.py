from sql import SQLighter
import re, time, os, random
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone,timedelta
import qrcode


class core:
    def __init__(self, telid=None, idd=None, base_dir=None, logger=None):
        self.logger = logger
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if base_dir == None else base_dir
        self._print("-------------------------")
        self.db = SQLighter(telid=telid, idd=idd, logger=logger)  # Модуль подключения к базе данных
        self.telid = telid  # Сохраняем ID чата в котором происходят эти сообщения
        self.user = self.db.user
        self.canwork = self.canworkcheck(telid or idd)
        self.logs = ''

    def _print(self, txt, type="INFO"):
        if self.logger == None:
            print("[{}] : {}".format(type, txt))
        else:
            type = type.lower()
            if type == "info" or type == 'i':
                self.logger.info(txt)
            if type == "warning" or type == 'w':
                self.logger.warning(txt)
            if type == "error" or type == 'e':
                self.logger.error(txt)

    def close(self,data=None, sent_info=None, mode=None):  # Обязательно закрываем базу данных
        print('close')
        print(data)
        if data is None: data={}
        pp = data.get('photo',[])
        if type(pp)!=list: pp = [pp]
        for p in pp:
            print(p)
            os.remove(p)

        pp = data.get('file', [])
        if type(pp) != list: pp = [pp]
        for p in pp:
            os.remove(p)

        live_update = data.get('live_update',False)
        if live_update:
            if live_update==2:
                self.db.live_update_update(mode="{};{}".format(data.get('command','sport'),sent_info),start=-1)
            self.db.live_update_update(mode="{};{}".format(data.get('command','sport'),sent_info))


        if data.get('error',False) is True:
            self.log_push('Close. Command = {}'.format(data.get('command','')))
            self.log_save(typ=5)
        else:
            self.log_save(mess=data.get('command',None),typ=1)
        self.db.close()

    def log_push(self,mess):
        self.logs += "{};".format(mess)

    def log_save(self,mess=None, typ=0):
        if mess==None: mess=self.logs
        self.db.log_add(typ=typ, message=mess)

    def canworkcheck(self, id):
        if id is None: return True
        if self.user: return True
        return False

    def detect_command(self,mess,verify=True):
        if verify: reg = re.match('^(\/[a-z]+)( ([0-9a-zA-ZÀ-ÿ\-\, ]+))?$',mess)
        else: reg = re.match('^(\/[a-z]+)( ([0-9a-zA-ZÀ-ÿ\-\/\n\'\,\.\:\; ]+))?$',mess)
        if reg is None: return None
        reg = reg.groups()
        comm = reg[0][1:]
        city = reg[2]
        if verify and comm not in ['travail', 'achats', 'sante', 'famille', 'handicap', 'sport', 'convocation', 'missions', 'enfants']:
            return None
        return (comm, city)

    def command(self,mess,messid=0,live_update=False):
        self.log_push(mess="COMMAND. mess = {}".format(mess))
        if not self.canwork:
            self.log_push(mess="Cannotwork")
            return {'mess': 'Try /start command','error':True}
        mess2 = self.detect_command(mess)
        if mess2 is None:
            self.log_push(mess="No right command '{}'; mess2 = {}".format(mess,mess2))
            return {'mess':'Not right format for command','error':True}
        comm, city = mess2
        self.log_push(mess="Command = {}".format(comm))
        self.log_push(mess="City = {}".format(city))

        if city and city=='-u':
            print("live update")
            live_update = 2
            city=None

        delay = 0
        if city and re.match('^\-[0-9]{1,2}$',city):
            delay = -int(city[1:])
            city=None
        if city and re.match('^\+[0-9]{1,2}$',city):
            delay = int(city[1:])
            city=None


        data = {
            'name': self.user['name'],
            'birthday': self.user['birthday'],
            'placeofbirth': self.user['placeofbirth'],
            'adress': self.user['adress'],
            'place': (self.user['place'] if city is None else city)
        }
        if None in data.values():
            self.log_push(mess="None in values. data = {}".format(data))
            return {'mess': 'You did not put all information. Use /edit command','error':True}
        return {'photo': createImage(data,typ=comm,delay=delay),'command':comm,'live_update':live_update}

    def text(self,mess, messid=0):
        self.log_push(mess="TEXT. mess = {}".format(mess))
        if not self.canwork:
            self.log_push(mess="Cannotwork")
            return {'mess':'Try /start command','error':True}
        mode = self.user['mode']
        self.log_push(mess="mode = {}".format(mode))
        if mode==0:
            self.log_push(mess="Nothing to analise")
            return {'mess':'Use commands to create a attestation','error':True}

        if mode==1:
            if re.match('^[a-zA-ZÀ-ÿ\- ]+$',mess) is None:
                self.log_push(mess="Not right format of name. mess = {}".format(mess))
                return {'mess':'Not right format of name. Should be:\nPrenom NOM','error':True}
            self.db.user_update(name=mess)
            self.db.user_set_mode(mode=2)
            return {'mess':'Now write date of your birthday in format:\nDD/MM/YYYY'}

        if mode==2:
            if re.match('^\d{2}\/\d{2}\/\d{4}$',mess) is None:
                self.log_push(mess="Not right format of birthday. mess = {}".format(mess))
                return {'mess':'Not right format of birthday. Should be:\nDD/MM/YYYY','error':True}
            self.db.user_update(birthday=mess)
            self.db.user_set_mode(mode=3)
            return {'mess':'Now your birthplace'}

        if mode==3:
            if re.match('^([0-9a-zA-ZÀ-ÿ\-\,\. ]+)$',mess) is None:
                self.log_push(mess="Not right format of birthplace. mess = {}".format(mess))
                return {'mess':'Not right format of birthplace','error':True}
            self.db.user_update(placeofbirth=mess)
            self.db.user_set_mode(mode=4)
            return {'mess':'Almost last. Write your address in format:\nAdresse Code Postal Ville'}

        if mode==4:
            if re.match('^([0-9a-zA-ZÀ-ÿ\-\,\. ]+)$',mess) is None:
                self.log_push(mess="Not right format of address. mess = {}".format(mess))
                return {'mess':'Not right format of address','error':True}
            self.db.user_update(adress=mess)
            self.db.user_set_mode(mode=5)
            return {'mess':'The last one. Write the place where you usually make this declaration'}

        if mode==5:
            if re.match('^([0-9a-zA-ZÀ-ÿ\-\,\. ]+)$',mess) is None:
                self.log_push(mess="Not right format of place. mess = {}".format(mess))
                return {'mess':'Not right format of place','error':True}
            self.db.user_update(place=mess)
            self.db.user_set_mode(mode=0)
            return {'mess':'Done. Now you can use commands for create attestation'}

    def toall(self,mess, messid=0):
        self.log_push(mess="TOALL. mess = {}".format(mess))
        if not self.canwork: return [self.telid], {'mess': 'Try /start command','error':True}
        if self.user.get('admin')<1:
            self.log_push(mess="Cannot use toall. admin = {}".format(mess))
            return [self.telid], {'mess': 'You dont have admin right to use this command','error':True}

        mess = self.detect_command(mess,verify=False)
        if mess is None or not mess[1]:
            self.log_push(mess="Not right fornat for command".format(mess))
            return [self.telid], {'mess': 'Not right format for command','error':True}
        comm, text = mess
        users = self.db.user_all()
        users = [u['telid'] for u in users]

        return users, {'mess': text}

    def test(self,mess,messid=0):
        if not self.canwork: return {}
        if self.user.get('admin')<1: return {}

        return {}



pos = {
    'name':(494,567),
    'birthday':(494,660),
    'placeofbirth':(1240,660),
    'adress':(545,751),
    'travail': (322,1025),
    'achats': (322,1213),
    'sante': (322,1445),
    'famille': (322,1616),
    'handicap': (322,1787),
    'sport': (322,1947),
    'convocation': (322,2208),
    'missions': (322,2370),
    'enfants': (322,2558),
    'place': (450, 2740),
    'date': (383, 2835),
    'time': (1065, 2835)
}

def createImage(data,typ='sport',fait=None,delay=0):
    image = getImage(data,typ,fait,delay=delay)
    name = ''.join([str(random.randint(0,9)) for i in range(10)])
    path = 'export/{}.png'.format(name)
    image.save(path, optimize=True, quality=95)
    return path

def getImage(data, typ='sport', fait=None,delay=0):
    if fait == None:
        now = (datetime.now()+timedelta(minutes=delay)).astimezone(timezone.utc)
        now = now.replace(tzinfo=timezone(timedelta(hours=-1)))
        fait = {'date': now.astimezone(timezone.utc).strftime("%d/%m/%Y"),
                'time': now.astimezone(timezone.utc).strftime("%Hh%M")}
    name = data['name'].split(' ')
    qr_data = 'Cree le: {creationDate} a {creationHour};\nNom: {lastname};\nPrenom: {firstname};\nNaissance: {birthday} a {placeofbirth};\nAdresse: {adress};\nSortie: {datesortie} a {heuresortie};\nMotifs: {reasons};\n'.format(
        creationDate=fait['date'],
        creationHour=fait['time'],
        lastname=' '.join([] if len(name)<2 else name[1:]),
        firstname=name[0],
        birthday=data['birthday'],
        placeofbirth=data['placeofbirth'],
        adress=data['adress'],
        datesortie=fait['date'],
        heuresortie=fait['time'],
        reasons="sport")

    if type(typ) == str: typ = [typ]

    print(data)

    image = Image.open('src/certificate.jpg')
    qr_img = qrcode.make(qr_data)
    qr_img = qr_img.resize((400, 400), Image.ANTIALIAS)
    x0, y0 = 1820, 2690
    image.paste(qr_img, (x0, y0, x0 + qr_img.size[0], y0 + qr_img.size[1]))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('Roboto-Regular.ttf', size=45)
    font2 = ImageFont.truetype('Roboto-Regular.ttf', size=85)
    color = 'rgb(0, 0, 0)'
    for k in data.keys():
        print(pos[k],data[k])
        draw.text(pos[k], str(data[k]), fill=color, font=font)
    for k in fait.keys():
        draw.text(pos[k], str(fait[k]), fill=color, font=font)
    for t in typ:
        draw.text(pos[t], 'x', fill=color, font=font2)

    return image