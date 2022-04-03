import subprocess
import argparse
import os
import graph_pb2 as tfGraph
from tensorflow.python.platform import gfile
from google.protobuf import text_format
import textwrap
import datetime
class Parse():
    def __init__(self):
        self.micron = 1000
        self.vertial_layers=[]
        self.horizontal_layers=[]
        self.cell_size = {} # dict of [w, h]
        self.macro_map = {}
        self.key2cell = {} # map inst string to macro name
        self.rotate_flag ={}# map inst to direction
        self.port_loc = {}
        self.port_edge = {}
        self.port_direc = {}
        self.node_connect={}
        self.info=''
        self.defile =''
        self.lefile=''
        self.design='Test'
        self.width = 0
        self.height = 0
        self.hor_track = 0
        self.ver_track = 0
    def print(self):
        print('micron:',self.micron)
        print('vertial_layers:',self.vertial_layers)
        print('horizontal_layers:',self.horizontal_layers)
        print('cell_size:',self.cell_size)
        print('macro_map:',self.macro_map)
        print('key2cell:',self.key2cell)
        print('rotate_flag:',self.rotate_flag)
        print('port_loc:',self.port_loc)
        print('port_direc:',self.port_direc)
        print('node_connect:',self.node_connect)
    def gen_dirc_tracks(self,layer_list):
        total_tracks=0
        for item in layer_list:
            total_tracks += 1 / float(item)
            # print('gen_tracks:',item,total_tracks)
        return round(total_tracks,6)
    def gen_tracks(self):
        self.hor_track = self.gen_dirc_tracks(self.horizontal_layers)
        self.ver_track = self.gen_dirc_tracks(self.vertial_layers)
        
    def parse_lef(self, file_name):
        assert os.path.exists(file_name), "File not found: {}".format(file_name)
        print("Parsing " + file_name)
        try:
            self.micron = float(subprocess.getoutput("grep \"DATABASE MICRONS\" {}".format(file_name)).strip().split()[2])
        except Exception as e:
            prin('warning micron in lef:',e)
        self.lefile = file_name
        with open(file_name) as f:
            lines = f.readlines()
            flag_macro = 0
            flag_macro_pin = 0
            flag_layer = 0
            flag_routing = 0
            flag_pin_layer = 0
            flag_dir = 1
            cur_macro = "NULL"
            cur_layer = "NULL"
            cur_macro_pin = "NULL"
            track_width = 0
            w =0
            h = 0
            for line in lines:
                segs = line.strip().split()
                if len(segs) == 0:
                    continue
                if flag_macro:
                    if "END {}".format(cur_macro) in line:
                        flag_macro = 0
                        continue
                    if "END {}".format(cur_macro_pin) in line:
                        if flag_macro:
                            if flag_macro_pin:
                                flag_macro_pin = 0
                                if flag_pin_layer:
                                    flag_pin_layer =0
                                    if (cur_macro_pin!="VDD" and cur_macro_pin!="VSS" ):
                                        tmp = cur_macro+'/'+cur_macro_pin
                                        if tmp not in self.macro_map:
                                            self.macro_map[tmp]=[pin_offset_x,pin_offset_y]
                    if "SIZE" == segs[0]:
                        w, h = float(segs[1]), float(segs[3])
                        self.cell_size[cur_macro] = [w, h]
                    if "PIN" == segs[0]:
                        flag_macro_pin = 1
                        cur_macro_pin = segs[1]
                    if flag_macro_pin:
                        if "LAYER M1" in line:
                            flag_pin_layer = 1
                    if flag_pin_layer:
                        if "RECT" == segs[0]:
                            x1,y1,x2,y2 = float(segs[1]), float(segs[2]),float(segs[3]), float(segs[4])
                            pin_offset_x = round(0.5*((x1+x2)- w),5)
                            pin_offset_y = round(0.5*((y1+y2)- h),5)
                if "MACRO" == segs[0]:
                    cur_macro = segs[1]
       
                    flag_macro = 1
                if flag_layer:
                    if "END {}".format(cur_layer) in line:
                        flag_layer = 0
                        if flag_routing:
                            if flag_dir ==0:
                                self.horizontal_layers.append(track_width)
                            else:
                                self.vertial_layers.append(track_width)
                            flag_routing = 0
                         
                        continue
                    if "TYPE" == segs[0]:
                        if "ROUTING" == segs[1]:
                            flag_routing = 1
                    if flag_routing:
                        if "DIRECTION" == segs[0]:
                            if segs[1] == "HORIZONTAL":
                                flag_dir = 0
                            else:
                                flag_dir = 1
                        if "PITCH" ==segs[0]:
                            tmp_pitch =float(segs[1])
                            if tmp_pitch >1:
                                tmp_pitch = tmp_pitch / self.micron 
                            track_width += tmp_pitch
                            
                        if "WIDTH" ==segs[0]:
                            tmp_width =float(segs[1])
                            if tmp_width >1:
                                tmp_width = tmp_width / self.micron
                            track_width += tmp_width
                if "LAYER" == segs[0]:
                    cur_layer = segs[1]
                    flag_layer = 1
                    track_width = 0
    def parse_def(self, file_name):
        
        assert os.path.exists(file_name), "File not found: {}".format(file_name)
        print("Parsing " + file_name)
        self.micron = float(subprocess.getoutput("grep \"UNITS DISTANCE MICRONS\" {}".format(file_name)).strip().split()[3])
        self.defile = file_name
        with open(file_name) as f:
            lines = f.readlines()
            flag_allnets = 0
            flag_net = 0
            flag_allpins = 0
            flag_property = 0
            flag_pin = 0
            flag_components = 0
            pin_name = ''
            cur_port =''
            cur_pin = ''
            net_cells = []
            cur_port_x = 0
            cur_port_y = 0
            cur_pins_list=[]
            direc =''
            for line in lines:
                segs = line.strip().split()
                if len(segs) == 0:
                    continue
                if flag_allpins:
                    if "END PINS" in line:
                        flag_allpins = 0
                        continue
                    if "+" == segs[0]:
                        if "PLACED" == segs[1]:
                            
                            if (cur_port!="VDD" and cur_port!="VSS" and len(cur_port)>0):
                                cur_port_x = round(float(segs[3])/self.micron,5)
                                cur_port_y = round(float(segs[4])/self.micron,5)
                                direc = segs[6]
                                self.port_direc[cur_port] = direc
                                self.port_loc[cur_port] = [cur_port_x,cur_port_y]
                    if "-" == segs[0]:
                        cur_port =segs[1]
                        continue
                    continue
                if flag_allnets:
                    if "END NETS" in line:
                        flag_allnets = 0
                        continue
                    if flag_net:
                        if "(" == segs[0]:
                            if "PIN" == segs[1]:
                                cur_pins_list.append(segs[2])
                            else:
                                tmp = segs[1] + '/'+segs[2]
                                cur_pins_list.append(tmp)
                    if "-" == segs[0]:
                        flag_net = 1
                        if len(cur_pins_list)>1:
                            for item in cur_pins_list:
                                if item not in self.node_connect:
                                    self.node_connect[item]=[]
                                for other in cur_pins_list:
                                    if item ==other:
                                        continue
                                    if other not in self.node_connect[item]:
                                        self.node_connect[item].append(other)
                        cur_pins_list=[]
                if flag_components:
                    if "END COMPONENTS" in line:
                        flag_components = 0
                        continue
                    if '-' == segs[0]:
                        self.key2cell[segs[1]] = segs[2]
                        if len(segs) > 9 and segs[9] in ["W", "E", "FW", "FE"]:
                            self.rotate_flag[segs[1]] = 1
                        else:
                            self.rotate_flag[segs[1]] = 0
                if  flag_property:
                    if "END PINPROPERTIES" in line:
                        flag_property =0
                        continue
                    if '-' == segs[0]:
                        cur_pin = segs[2]
                        assert cur_pin in self.port_loc, "{} not in port map".format(cur_pin)
                    if '+' == segs[0]:  
                        if len(segs)>4:
                            propers = segs[4].strip().split('"')[0]
                            if propers in ['top','bottom','left','right']:
                                self.port_edge[cur_pin] = propers
                            else:
                                print('not find dirc:',propers,segs[4])
                if "COMPONENTS" == segs[0]:
                    flag_components = 1
                    continue
                if "PINS" == segs[0]:
                    flag_allpins = 1
                    continue
                if "NETS" == segs[0]:
                    flag_allnets = 1
                    continue
                if "PINPROPERTIES" == segs[0]:
                    flag_property = 1
                    continue
                if "DESIGN" == segs[0]:
                    self.design = segs[1]
                if "DIEAREA" == segs[0]:
                    self.width =round( (float(segs[10]) - float(segs[6]))/self.micron,5)
                    self.height = round((float(segs[7]) - float(segs[3]))/self.micron,5)
    def gen_info(self):
        self.info = textwrap.dedent("""\
        # Placement file for Circuit Training
        # Source input file(s) : {src_filename}
        # This file : {filename}
        # Date : {date}
        # Columns : {cols}  Rows : {rows}
        # Width : {width:.3f}  Height : {height:.3f}
        # Area : {area}
        # Project : {project}
        # Block : {block_name}
        # Routes per micron, hor : {hor_routes:.3f}  ver : {ver_routes:.3f}
        # Routes used by macros, hor : {hor_macro_alloc:.3f}  ver : {ver_macro_alloc:.3f}
        # Smoothing factor : {smooth}
        # Overlap threshold : {overlap_threshold}
      """.format(
          src_filename=self.defile,
          filename=self.lefile,
          date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
          cols=int( self.width/10),
          rows=int( self.height/10),
          width=self.width,
          height=self.height,
          area=round(self.width*self.height,5),
          project=self.design,
          block_name=self.design,
          hor_routes=self.hor_track,
          ver_routes=self.ver_track,
          hor_macro_alloc=51.79,
          ver_macro_alloc=51.79,
          smooth=2,
          overlap_threshold=0.004))

        self.info += '\n# Counts of node types:\n'
        self.info += '\n# node_index x y orientation fixed'
    def gen_node(self):
        with open('initial.plc', 'w+', encoding="utf-8") as file:
            self.gen_tracks()
            self.gen_info()
            
            file.write(self.info)
        #if len(self.node_connect)>0:
            g=tfGraph.GraphDef()
            item_id = 0
            for key in self.node_connect:
                offset_x =''
                offset_y = ''
                port_x =''
                port_y = ''
                inputs = []
                side=''
                dirc = '-'
                fixed = 0
                node = g.node.add()
                if '/' in key:#macro pin
                    inst,pin = key.split('/')
                    if inst in self.key2cell:
                        macro = self.key2cell[inst]
                        macro_pin = macro + '/' + pin
                        offset_x,offset_y = self.macro_map[macro_pin]
                        if inst in self.rotate_flag:
                            if self.rotate_flag[inst]==0:
                                dirc = 'N'
                            else:
                                dirc = 'S'
                        else:
                            dirc = '-'
                    else:
                        print('not find inst reference macro:',inst)
                        print( self.key2cell)
                    assert inst in self.key2cell
                    
                    node.name = macro_pin
                    node.attr['macro_name'].placeholder = macro
                    node.attr['type'].placeholder = str("macro_pin")
                    node.attr['x_offset'].f = round(float(offset_x),5)
                    node.attr['y_offset'].f = round(float(offset_y),5)
                else:#port
                    if key in self.port_loc:
                        port_x,port_y = self.port_loc[key]
                        side = self.port_edge[key]
                    else:
                        print('not find port:',key)
                        print(self.port_loc)
                    assert key in self.port_loc
                    node.name = key
                    node.attr['site'].placeholder = str(side).upper()
                    node.attr['type'].placeholder = str("PORT")
                    node.attr['x'].f = round(float(port_x),5)
                    node.attr['y'].f = round(float(port_y),5)
                    dirc = self.port_direc[key]
                    fixed =1
                    plc_item = str(item_id) + ' '+str(port_x) + ' '+str(port_y)+' '+dirc+' '+str(fixed)
                    file.write(plc_item+"\n")
                if key in self.node_connect:
                    inputs = self.node_connect[key]
                else:
                    print('not find node connect:',key)
                assert key in self.node_connect
                for item in inputs:
                    node.input.append(item)
                
                
                item_id+=1
            for key in self.key2cell:
                value = self.key2cell[key]
                fixed = 0
                if key in self.rotate_flag:
                    tmp_dirc = self.rotate_flag[key]
                    if tmp_dirc ==0:
                        dirc = 'N'
                    else:
                        dirc ='S'
                else:
                    dirc ='-'
                
                w,h = self.cell_size[value]
                node_macro = g.node.add()
                node_macro.name = key
                node_macro.attr['type'].placeholder = str("macro")
                if not dirc=='-':
                    node_macro.attr['orientation'].placeholder = dirc
                node_macro.attr['width'].f = round(float(w),5)
                node_macro.attr['height'].f = round(float(h),5)
                plc_item = str(item_id) + ' '+str(0) + ' '+str(0)+' '+dirc+' '+str(fixed)
                file.write(plc_item+"\n")
                item_id+=1
            txtfile='netlist.pb.txt'
            with gfile.FastGFile(txtfile, 'wb') as f:
              
              f.write(text_format.MessageToString(g))
if __name__=='__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--lefin', type=str, help="lef file to provide netlist")
    argparser.add_argument('--defin', type=str, help="def file to provide netlist")
    dh= Parse()
    args = argparser.parse_args()
    dh.parse_lef(args.lefin)
    dh.parse_def(args.defin)
    dh.print()
    dh.gen_node()