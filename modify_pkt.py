

import os
import sys
import xml.etree.ElementTree as ET
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKT_TOOL   = os.path.join(SCRIPT_DIR, 'pkt_tool.py')
BACKUP_PKT = os.path.join(SCRIPT_DIR, 'tema1_backup.pkt')
OUTPUT_PKT = os.path.join(SCRIPT_DIR, 'tema1.pkt')
TMP_XML_IN = '/tmp/tema1_orig_clean.xml'
TMP_XML_OUT= '/tmp/tema1_fixed.xml'


print("=== Step 0: Decrypting backup PKT → XML ===")
subprocess.run(['python3', PKT_TOOL, '-d', BACKUP_PKT, TMP_XML_IN], check=True)

tree = ET.parse(TMP_XML_IN)
root = tree.getroot()


devices = root.findall('.//NETWORK/DEVICES/DEVICE')
name_to_eng = {}
ref_to_name = {}
for dev in devices:
    eng = dev.find('ENGINE')
    if eng is None: continue
    name_e = eng.find('NAME')
    ref_e  = eng.find('SAVE_REF_ID')
    if name_e is not None:
        name_to_eng[name_e.text] = eng
        if ref_e is not None:
            ref_to_name[ref_e.text] = name_e.text


sw_ports = {}   
links = root.findall('.//NETWORK/LINKS/LINK')
for link in links:
    cable = link.find('CABLE')
    if cable is None: continue
    from_ref = to_ref = None
    ports = []
    for sub in cable:
        if sub.tag == 'FROM':  from_ref = sub.text
        elif sub.tag == 'TO':  to_ref = sub.text
        elif sub.tag == 'PORT': ports.append(sub.text)
    if from_ref and to_ref and len(ports) >= 2:
        n1 = ref_to_name.get(from_ref, '')
        n2 = ref_to_name.get(to_ref, '')
        if n1 == 'Switch1': sw_ports[ports[0]] = n2
        elif n2 == 'Switch1': sw_ports[ports[1]] = n1






dept_devs = {
    : {'vlan': 10, 'net': '192.168.100', 'devs': ['PC0','PC1','Printer0','Printer0(1)']},
    :        {'vlan': 20, 'net': '192.168.200', 'devs': ['PC2','PC3','PC4','PC5','PC6','PC7']},
    :        {'vlan': 30, 'net': '192.168.30',  'devs': ['PC8','PC9','PC10','PC11','PC12','PC13','PC14','PC15']},
    :          {'vlan': 40, 'net': '192.168.40',  'devs': ['PC16','Server0']},
}
dev_to_vlan = {}
dev_to_gw = {}
for d, info in dept_devs.items():
    for device in info['devs']:
        dev_to_vlan[device] = info['vlan']
        dev_to_gw[device]   = info['net'] + '.1'

def set_or_create(parent, tag, val):
    
    e = parent.find(tag)
    if e is None: e = ET.SubElement(parent, tag)
    e.text = val




print("=== Step 1: Switch1 — VLANs + trunk ===")
sw_lines = [
    , "version 15.0", "no service timestamps log datetime msec",
    , "no service password-encryption", "!",
    , "!", "!", "!", "!", "!", "!",
    , "spanning-tree extend system-id", "!",
    , " switchport mode trunk", "!",
]
for port_idx in range(2, 25):
    pname = f"FastEthernet0/{port_idx}"
    attached = sw_ports.get(pname)
    vlan = dev_to_vlan.get(attached)
    sw_lines.append(f"interface {pname}")
    if vlan:
        sw_lines.append(f" switchport access vlan {vlan}")
        sw_lines.append(f" switchport mode access")
    sw_lines.append("!")
sw_lines += [
    , "!", "interface GigabitEthernet0/2", "!",
    , " no ip address", " shutdown", "!",
    , "!", "line con 0", "!",
    , " login", "line vty 5 15", " login", "!", "!", "!", "end",
]

sw_eng = name_to_eng.get('Switch1')
if sw_eng is not None:
    for tag in ['RUNNINGCONFIG', 'STARTUPCONFIG']:
        e = sw_eng.find(tag)
        if e is not None:
            for c in list(e): e.remove(c)
            for l in sw_lines: ET.SubElement(e, 'LINE').text = l




print("=== Step 2: Router2 — subinterfaces + DHCP ===")
rt_lines = [
    , "version 15.1", "no service timestamps log datetime msec",
    , "no service password-encryption", "!",
    , "!", "!", "!", "!",
    
    ,
    ,
    ,
    , "!",
    , " network 192.168.100.0 255.255.255.0",
    , " dns-server 192.168.40.2",
    , " network 192.168.200.0 255.255.255.0",
    , " dns-server 192.168.40.2",
    , " network 192.168.30.0 255.255.255.0",
    , " dns-server 192.168.40.2",
    , " network 192.168.40.0 255.255.255.0",
    , " dns-server 192.168.40.2",
    , "!", "!", "ip cef", "no ipv6 cef", "!", "!", "!", "!",
    ,
    , "!", "!", "!", "!", "!", "!", "!", "!", "!", "!", "!", "!",
    , "!", "!", "!", "!", "!", "!",
    
    , " no ip address", " duplex auto", " speed auto", " no shutdown", "!",
    , " encapsulation dot1Q 10", " ip address 192.168.100.1 255.255.255.0", "!",
    , " encapsulation dot1Q 20", " ip address 192.168.200.1 255.255.255.0", "!",
    , " encapsulation dot1Q 30", " ip address 192.168.30.1 255.255.255.0", "!",
    , " encapsulation dot1Q 40", " ip address 192.168.40.1 255.255.255.0", "!",
    , " no ip address", " duplex auto", " speed auto", " shutdown", "!",
    , " no ip address", " shutdown", "!",
    , "!", "ip flow-export version 9",
    , "!", "!", "!", "!", "!", "!",
    , "!", "line aux 0", "!", "line vty 0 4", " login", "!", "!", "!", "end",
]

rt_eng = name_to_eng.get('Router2')
if rt_eng is not None:
    for tag in ['RUNNINGCONFIG', 'STARTUPCONFIG']:
        e = rt_eng.find(tag)
        if e is not None:
            for c in list(e): e.remove(c)
            for l in rt_lines: ET.SubElement(e, 'LINE').text = l
    
    for port in rt_eng.iter('PORT'):
        pt = port.find('TYPE')
        if pt is not None and 'GigabitEthernet' in (pt.text or ''):
            pn = port.find('PORTNAME')
            if pn is not None and pn.text == 'GigabitEthernet0/0':
                admin = port.find('ADMIN_DOWN')
                if admin is not None: admin.text = 'false'
                power = port.find('POWER')
                if power is not None: power.text = 'true'




print("=== Step 3: PCs/Printers — DHCP + DNS hint ===")
dhcp_devs = (dept_devs['Secretariat']['devs'] + dept_devs['Lab1']['devs']
             + dept_devs['Lab2']['devs'] + ['PC16'])
for dname in dhcp_devs:
    eng = name_to_eng.get(dname)
    if eng is None: continue
    for port in eng.iter('PORT'):
        pt = port.find('TYPE')
        if pt is not None and 'FastEthernet' in (pt.text or ''):
            set_or_create(port, 'PORT_DNS',     '192.168.40.2')
            set_or_create(port, 'HOST_DNS',     '192.168.40.2')
            set_or_create(port, 'PORT_GATEWAY', dev_to_gw[dname])
            set_or_create(port, 'HOST_GATEWAY', dev_to_gw[dname])
            set_or_create(port, 'PORT_DHCP_ENABLE', 'true')
            break




print("=== Step 4: Server0 — static IP + DNS + HTTP ===")
srv = name_to_eng.get('Server0')
if srv is not None:
    
    for port in srv.iter('PORT'):
        pt = port.find('TYPE')
        if pt is not None and 'FastEthernet' in (pt.text or ''):
            for t, v in [('IP','192.168.40.2'), ('SUBNET','255.255.255.0'),
                         ('HOST_IP','192.168.40.2'), ('HOST_MASK','255.255.255.0'),
                         ('HOST_GATEWAY','192.168.40.1'), ('HOST_DNS','192.168.40.2'),
                         ('PORT_GATEWAY','192.168.40.1'), ('PORT_DNS','192.168.40.2')]:
                set_or_create(port, t, v)
            set_or_create(port, 'PORT_DHCP_ENABLE', 'false')
            break

    
    dns_srv = srv.find('DNS_SERVER')
    if dns_srv is not None:
        set_or_create(dns_srv, 'ENABLED', '1')
        ns_db = dns_srv.find('NAMESERVER-DATABASE')
        if ns_db is None: ns_db = ET.SubElement(dns_srv, 'NAMESERVER-DATABASE')
        for c in list(ns_db): ns_db.remove(c)
        for domain in ['www.scoala.ro', 'scoala.ro']:
            rec = ET.SubElement(ns_db, 'RESOURCE-RECORD')
            ET.SubElement(rec, 'TYPE').text      = 'A-REC'
            ET.SubElement(rec, 'NAME').text       = domain
            ET.SubElement(rec, 'TTL').text        = '86400'
            ET.SubElement(rec, 'IPADDRESS').text  = '192.168.40.2'

    
    http_srv = srv.find('HTTP_SERVER')
    if http_srv is not None:
        set_or_create(http_srv, 'ENABLED', '1')
    fm = srv.find('FILE_MANAGER')
    root_dir = fm.find('FILE')       
    root_files = root_dir.find('FILES')
    for fs_dir in root_files:
        fn = fs_dir.find('NAME')
        if fn is not None and fn.text == 'http:':
            for f in fs_dir.find('FILES'):
                if f.find('NAME').text == 'index.html':
                    fc = f.find('FILE_CONTENT')
                    text_e = fc.find('TEXT')
                    if text_e is None: text_e = ET.SubElement(fc, 'TEXT')
                    text_e.text = (
                        
                        
                        
                        
                        
                        
                        
                    )
                    break


print("=== Step 5: Saving XML → encrypting PKT ===")
tree.write(TMP_XML_OUT, encoding='unicode', xml_declaration=False)
subprocess.run(['python3', PKT_TOOL, '-e', TMP_XML_OUT, OUTPUT_PKT], check=True)

print(f"\n✅  Done!  Output: {OUTPUT_PKT}")
print("    Open this file in Packet Tracer (Ctrl+O, do NOT save the old one).")
