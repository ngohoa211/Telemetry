from __future__ import print_function
import sys
import argparse
import libvirt
from lxml import etree
import sched
import time
from prometheus_client import start_http_server, Gauge
from xml.etree import ElementTree
# https://github.com/ngohoa211/ceilometer/blob/stable/queens/ceilometer/compute/virt/libvirt/inspector.py
#https://gist.github.com/VeenaSL/606e1771cadbae36d4b55685398e4835
# https://python-forum.io/Thread-Parse-XML-with-Namespaces
# <domain type='kvm' id='4'>
#   <name>instance-00000010</name>
#   <uuid>ae7fb5a8-b0fa-4714-8880-747d15d28416</uuid>
#   <metadata>
#     <nova:instance xmlns:nova="http://openstack.org/xmlns/libvirt/nova/1.0">
#       <nova:package version="17.0.7"/>
#       <nova:name>au-aleup_group-2jkw6dymlqgm-4r6mbscjpkdd-iqlzyhulwnry</nova:name>
#       <nova:creationTime>2019-05-20 04:46:49</nova:creationTime>
#       <nova:flavor name="m1.tiny">
#         <nova:memory>512</nova:memory>
#         <nova:disk>1</nova:disk>
#         <nova:swap>0</nova:swap>
#         <nova:ephemeral>0</nova:ephemeral>
#         <nova:vcpus>1</nova:vcpus>
#       </nova:flavor>
#       <nova:owner>
#         <nova:user uuid="40b8e0abb02745a5a4dcf771777cec4c">demo</nova:user>
#         <nova:project uuid="807fde4f91504c18989f32e046240e9e">demo</nova:project>
#       </nova:owner>
#       <nova:root type="image" uuid="f11180a5-1a7c-45b2-b6a0-c94c96e15d63"/>
#     </nova:instance>
#   </metadata>
#   <memory unit='KiB'>524288</memory>
#   <currentMemory unit='KiB'>524288</currentMemory>
#   <vcpu placement='static'>1</vcpu>
#   <cputune>
#     <shares>1024</shares>
#   </cputune>
#   <resource>
#     <partition>/machine</partition>
#   </resource>
#   <sysinfo type='smbios'>
#     <system>
#       <entry name='manufacturer'>OpenStack Foundation</entry>
#       <entry name='product'>OpenStack Nova</entry>
#       <entry name='version'>17.0.7</entry>
#       <entry name='serial'>4f0a00b2-0edd-49e9-9107-c5e1eba37e87</entry>
#       <entry name='uuid'>ae7fb5a8-b0fa-4714-8880-747d15d28416</entry>
#       <entry name='family'>Virtual Machine</entry>
#     </system>
#   </sysinfo>
#   <os>
#     <type arch='x86_64' machine='pc-i440fx-bionic'>hvm</type>
#     <boot dev='hd'/>
#     <smbios mode='sysinfo'/>
#   </os>
#   <features>
#     <acpi/>
#     <apic/>
#   </features>
#   <cpu mode='custom' match='exact' check='full'>
#     <model fallback='forbid'>Nehalem-IBRS</model>
#     <vendor>Intel</vendor>
#     <topology sockets='1' cores='1' threads='1'/>
#     <feature policy='require' name='vme'/>
#     <feature policy='require' name='ss'/>
#     <feature policy='require' name='vmx'/>
#     <feature policy='require' name='x2apic'/>
#     <feature policy='require' name='tsc-deadline'/>
#     <feature policy='require' name='hypervisor'/>
#     <feature policy='require' name='arat'/>
#     <feature policy='require' name='tsc_adjust'/>
#     <feature policy='require' name='ssbd'/>
#     <feature policy='require' name='rdtscp'/>
#   </cpu>
#   <clock offset='utc'>
#     <timer name='pit' tickpolicy='delay'/>
#     <timer name='rtc' tickpolicy='catchup'/>
#     <timer name='hpet' present='no'/>
#   </clock>
#   <on_poweroff>destroy</on_poweroff>
#   <on_reboot>restart</on_reboot>
#   <on_crash>destroy</on_crash>
#   <devices>
#     <emulator>/usr/bin/kvm-spice</emulator>
#     <disk type='network' device='disk'>
#       <driver name='qemu' type='raw' cache='none'/>
#       <auth username='volumes'>
#         <secret type='ceph' uuid='457eb676-33da-42ec-9a8c-9293d545c337'/>
#       </auth>
#       <source protocol='rbd' name='volumes/ae7fb5a8-b0fa-4714-8880-747d15d28416_disk'>
#         <host name='192.168.1.211' port='6789'/>
#         <host name='192.168.1.212' port='6789'/>
#         <host name='192.168.1.213' port='6789'/>
#       </source>
#       <target dev='vda' bus='virtio'/>
#       <alias name='virtio-disk0'/>
#       <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
#     </disk>
#     <controller type='usb' index='0' model='piix3-uhci'>
#       <alias name='usb'/>
#       <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x2'/>
#     </controller>
#     <controller type='pci' index='0' model='pci-root'>
#       <alias name='pci.0'/>
#     </controller>
#     <interface type='bridge'>
#       <mac address='fa:16:3e:78:02:77'/>
#       <source bridge='qbrcff41163-56'/>
#       <target dev='tapcff41163-56'/>
#       <model type='virtio'/>
#       <mtu size='1500'/>
#       <alias name='net0'/>
#       <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
#     </interface>
#     <serial type='pty'>
#       <source path='/dev/pts/24'/>
#       <log file='/var/lib/nova/instances/ae7fb5a8-b0fa-4714-8880-747d15d28416/console.log' append='off'/>
#       <target type='isa-serial' port='0'>
#         <model name='isa-serial'/>
#       </target>
#       <alias name='serial0'/>
#     </serial>
#     <console type='pty' tty='/dev/pts/24'>
#       <source path='/dev/pts/24'/>
#       <log file='/var/lib/nova/instances/ae7fb5a8-b0fa-4714-8880-747d15d28416/console.log' append='off'/>
#       <target type='serial' port='0'/>
#       <alias name='serial0'/>
#     </console>
#     <input type='tablet' bus='usb'>
#       <alias name='input0'/>
#       <address type='usb' bus='0' port='1'/>
#     </input>
#     <input type='mouse' bus='ps2'>
#       <alias name='input1'/>
#     </input>
#     <input type='keyboard' bus='ps2'>
#       <alias name='input2'/>
#     </input>
#     <graphics type='vnc' port='5900' autoport='yes' listen='0.0.0.0' keymap='en-us'>
#       <listen type='address' address='0.0.0.0'/>
#     </graphics>
#     <video>
#       <model type='cirrus' vram='16384' heads='1' primary='yes'/>
#       <alias name='video0'/>
#       <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
#     </video>
#     <memballoon model='virtio'>
#       <stats period='10'/>
#       <alias name='balloon0'/>
#       <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
#     </memballoon>
#   </devices>
#   <seclabel type='dynamic' model='apparmor' relabel='yes'>
#     <label>libvirt-ae7fb5a8-b0fa-4714-8880-747d15d28416</label>
#     <imagelabel>libvirt-ae7fb5a8-b0fa-4714-8880-747d15d28416</imagelabel>
#   </seclabel>
#   <seclabel type='dynamic' model='dac' relabel='yes'>
#     <label>+64055:+130</label>
#     <imagelabel>+64055:+130</imagelabel>
#   </seclabel>
# </domain>

parser = argparse.ArgumentParser(description='libvirt_exporter scrapes domains metrics from libvirt daemon')
parser.add_argument('-si','--scrape_interval', help='scrape interval for metrics in seconds', default= 5)
parser.add_argument('-uri','--uniform_resource_identifier', help='Libvirt Uniform Resource Identifier', default= "qemu:///system")

args = vars(parser.parse_args())
uri = args["uniform_resource_identifier"]


def connect_to_uri(uri):
    conn = libvirt.open(uri)

    if conn == None:
        print('Failed to open connection to ' + uri, file = sys.stderr)
    else:
        print('Successfully connected to ' + uri)
    return conn


def get_domains(conn):

    domains = []

    for id in conn.listDomainsID():
        dom = conn.lookupByID(id)

        if dom == None:
            print('Failed to find the domain ' + dom.name(), file=sys.stderr)
        else:
            domains.append(dom)

    if len(domains) == 0:
        print('No running domains in URI')
        return None
    else:
        return domains


def get_metrics_collections(metric_names, labels, stats):
    dimensions = []
    metrics_collection = {}

    for mn in metric_names:
        if type(stats) is list:
            dimensions = [[stats[0][mn], labels]]
        elif type(stats) is dict:
            dimensions = [[stats[mn], labels]]
        metrics_collection[mn] = dimensions

    return metrics_collection


def get_metrics_multidim_collections(dom, metric_names, device):

    tree = ElementTree.fromstring(dom.XMLDesc())
    targets = []

    for target in tree.findall("devices/" + device + "/target"): # !
        targets.append(target.get("dev"))

    metrics_collection = {}

    for mn in metric_names:
        dimensions = []
        for target in targets:
            labels = {'domain': dom.name()}
            labels['target_device'] = target
            if device == "interface":
                stats = dom.interfaceStats(target) # !
            elif device == "disk":
                stats= dom.blockStats(target)
            stats = dict(zip(metric_names, stats))
            dimension = [stats[mn], labels]
            dimensions.append(dimension)
            labels = None
        metrics_collection[mn] = dimensions

    return metrics_collection


def add_metrics(dom, header_mn, g_dict):
    tree = etree.fromstring(dom.XMLDesc(0))
    username = tree.xpath('//domain/metadata/nova:instance/nova:owner/nova:user/text()',
                     namespaces={'nova':'http://openstack.org/xmlns/libvirt/nova/1.0'})
    labels = {'domain':dom.name(), 'username': username }
    print (labels)
    if header_mn == "libvirt_cpu_stats_":

        stats = dom.getCPUStats(True)
        metric_names = stats[0].keys()
        metrics_collection = get_metrics_collections(metric_names, labels, stats)
        unit = "_nanosecs"

    elif header_mn == "libvirt_mem_stats_":
        stats = dom.memoryStats()
        metric_names = stats.keys()
        metrics_collection = get_metrics_collections(metric_names, labels, stats)
        unit = ""

    elif header_mn == "libvirt_block_stats_":

        metric_names = \
        ['read_requests_issued',
        'read_bytes' ,
        'write_requests_issued',
        'write_bytes',
        'errors_number']

        metrics_collection = get_metrics_multidim_collections(dom, metric_names, device="disk")
        unit = ""

    elif header_mn == "libvirt_interface_":

        metric_names = \
        ['read_bytes',
        'read_packets',
        'read_errors',
        'read_drops',
        'write_bytes',
        'write_packets',
        'write_errors',
        'write_drops']

        metrics_collection = get_metrics_multidim_collections(dom, metric_names, device="interface")
        unit = ""

    for mn in metrics_collection:
        metric_name = header_mn + mn + unit
        dimensions = metrics_collection[mn]

        if metric_name not in g_dict.keys():

            metric_help = 'help'
            labels_names = metrics_collection[mn][0][1].keys()

            g_dict[metric_name] = Gauge(metric_name, metric_help, labels_names)

            for dimension in dimensions:
                dimension_metric_value = dimension[0]
                dimension_label_values = dimension[1].values()
                g_dict[metric_name].labels(*dimension_label_values).set(dimension_metric_value)
        else:
            for dimension in dimensions:
                dimension_metric_value = dimension[0]
                dimension_label_values = dimension[1].values()
                g_dict[metric_name].labels(*dimension_label_values).set(dimension_metric_value)
    return g_dict


def job(uri, g_dict, scheduler):
    print('BEGIN JOB :', time.time())
    conn = connect_to_uri(uri)
    domains = get_domains(conn)

    while domains is None:
        domains = get_domains(conn)
        time.sleep(int(args["scrape_interval"]))

    headers_mn = ["libvirt_cpu_stats_", "libvirt_mem_stats_", \
                  "libvirt_block_stats_", "libvirt_interface_"]

    for dom in domains:
        print(dom.name())

        for header_mn in headers_mn:
            g_dict = add_metrics(dom, header_mn, g_dict)

    conn.close()
    print('FINISH JOB :', time.time())
    scheduler.enter((int(args["scrape_interval"])), 1, job, (uri, g_dict, scheduler))


def main():

    start_http_server(9177)

    g_dict = {}

    scheduler = sched.scheduler(time.time, time.sleep)
    print('START:', time.time())
    scheduler.enter(0, 1, job, (uri, g_dict, scheduler))
    scheduler.run()

if __name__ == '__main__':
    main()
