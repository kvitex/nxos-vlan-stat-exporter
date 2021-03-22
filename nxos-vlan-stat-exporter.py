#!/usr/bin/env python3
import xmltodict
import os
from ncclient import manager
from dotenv import load_dotenv
from flask import Flask
from flask import request



load_dotenv()
user             = os.environ['DEVICE_USER']
password         = os.environ['DEVICE_PASSWORD']
metrics_name_prefix = os.environ.get('METRICS_NAME_PREFIX', '')

vlan_counters_names = {
            'mod:vlanshowbr-vlanid' : 'vlan_id',
            'mod:l2_ing_ucast_b'    : 'ifHCInOctets',
            'mod:l2_ing_ucast_p'    : 'ifHCInUcastPkts',
            'mod:l2_ing_mcast_b'    : 'ifHCInMulticastOctets',
            'mod:l2_ing_mcast_p'    : 'ifHCInMulticastPkts',
            'mod:l2_ing_bcast_b'    : 'ifHCInBroadcastOctets',
            'mod:l2_ing_bcast_p'    : 'ifHCInBroadcastPkts',
            'mod:l2_egr_ucast_b'    : 'ifHCOutOctets',
            'mod:l2_egr_ucast_p'    : 'ifHCOutUcastPkts',
            'mod:l3_ucast_rcv_b'    : 'l3_ucast_rcv_b',
            'mod:l3_ucast_rcv_p'    : 'l3_ucast_rcv_p'
}


vlan_list_req     = '''
                        <show xmlns="http://www.cisco.com/nxos:1.0">
                            <vlan>
                            
                            </vlan>
                        </show>
                       '''
vlan_counters_req = '''
                        <show xmlns="http://www.cisco.com/nxos:1.0">
                            <vlan>
                            <counters/>
                            </vlan>
                        </show>
                       '''

app = Flask(__name__)
@app.route('/metrics', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        hostname = request.form.get('hostname')
        port = request.form.get('port',22)
    else:
        hostname = request.args.get('hostname')
        port = request.form.get('port',22)
    if not hostname:
        return('Missing parameter: hostname')
    with manager.connect(host=hostname,
                         port=port,
                         username=user,
                         password=password,
                         hostkey_verify=False,
                         device_params={'name': 'nexus'},
                         allow_agent=False,
                         look_for_keys=False
                         ) as cisco_manager:
        rpc_reply = cisco_manager.get(('subtree', vlan_list_req))
        rpc_reply_dict = xmltodict.parse(str(rpc_reply),force_list={'vlan_mgr_cli:ROW_vlanbrief'})['rpc-reply']['data']['vlan_mgr_cli:show']['vlan_mgr_cli:vlan']['vlan_mgr_cli:__XML__OPT_Cmd_show_vlan___readonly__']['vlan_mgr_cli:__readonly__']['vlan_mgr_cli:TABLE_vlanbrief']['vlan_mgr_cli:ROW_vlanbrief']
        vlans = {}
        for vlan in rpc_reply_dict:
            vlans[str(vlan['vlan_mgr_cli:vlanshowbr-vlanid'])] = {
                'name': vlan['vlan_mgr_cli:vlanshowbr-vlanname'],
                'state': vlan['vlan_mgr_cli:vlanshowbr-vlanstate'],
                'shutstate': vlan['vlan_mgr_cli:vlanshowbr-shutstate'], 
                'ports': vlan.get('vlan_mgr_cli:vlanshowplist-ifidx','')
                }
        metrics= []
        for vlan_id in vlans:
            vlan = vlans[vlan_id]
            labels = [
                ('vlan_id','"{}"'.format(vlan_id)),
                ('ports', '"{}"'.format(vlans[vlan_id]['ports'])),
                ('name', '"{}"'.format(vlan['name']))
            ]
            metrics.append(
                {
                    'name': 'state',
                    'value': int(vlan['state'] == 'active'),
                    'labels': labels
                }
            )
            metrics.append(
                {
                    'name': 'shutstate',
                    'value': int(vlan['shutstate'] != 'noshutdown'),
                    'labels': labels
                }
            )
        rpc = cisco_manager.get(('subtree', vlan_counters_req))
        vlan_stat = xmltodict.parse(str(rpc),force_list={'mod:ROW_vlancounters'})
        rpc_reply_list = vlan_stat['rpc-reply']['data']['mod:show']['mod:vlan']['mod:counters']['mod:__XML__OPT_Cmd_show_vlan_counters___readonly__']['mod:__readonly__']['mod:TABLE_vlancounters']['mod:ROW_vlancounters']
        for vlan in rpc_reply_list:
            vlan_id = vlan['mod:vlanshowbr-vlanid']
            if vlans.get(vlan_id) is not None:
                labels = [
                    ('vlan_id', '"{}"'.format(vlan_id)),
                    ('ports', '"{}"'.format(vlans[vlan_id]['ports'])),
                    ('name', '"{}"'.format(vlans[vlan_id]['name'])),
                    ('ifName', '"VLAN{}"'.format(vlan_id)),
                    ('ifAlias', '"{}"'.format(vlans[vlan_id]['name'])),
                    ('ifDescr', '"VLAN{}"'.format(vlan_id))
                ]
                for counter_name in vlan:
                    metrics.append(
                        {
                            'name': vlan_counters_names[counter_name],
                            'value': vlan[counter_name],
                            'labels': labels
                        }
                    )
    output_list = []
    for metric in metrics:
        metric_name = metric['name']
        metric_value = metric['value']
        labels_string = ','.join(list(map(lambda st: '='.join(st), metric['labels'])))
        output_list.append(f'{metrics_name_prefix}{metric_name} {{{labels_string}}} {metric_value}')
    return '\n'.join(output_list)
