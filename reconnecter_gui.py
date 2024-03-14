from subprocess import Popen
import subprocess
from time import sleep
import datetime
import os
import winsound
from sys import argv

import wx
import threading

from reconnecter_result import reconnecter_result

AUDIBLE = False
VERBOSE = False

if len(argv) > 0:
  for i in range(len(argv)):
    match argv[i]:
      case("-a"):
        AUDIBLE = True
      case("-v"):
        VERBOSE = True

        
#logging:
if not os.path.exists('./log'):
  os.mkdir('log')
  
log_file_path = "./log/reconnecter" + str(datetime.datetime.now()) + ".log"
log_file_path = log_file_path.replace(" ", "-")
log_file_path = log_file_path.replace(":", "-")

logged_messages = []

def flush_logged_messages():
  global logged_messages
  res = logged_messages.copy()
  logged_messages = []
  return res

def log(msg):
  with open(log_file_path, "a") as log_f:
    now_str = str(datetime.datetime.now())
    log_str = f"{now_str}: {msg}"
    log_f.write(log_str)
    log_f.write('\n\n')

    if VERBOSE:
      print(log_str)
    
    logged_messages.append(log_str)
    


      
#util functions:
def run_proc(cmd):
  p = Popen(cmd, stdout=subprocess.PIPE)
  p_out, p_err = p.communicate()
  return str(p_out)

# parses command output for netsh commands - NOT for batch file's echo output
def parse_cmd_output(msg):
  return msg.split("\\r\\n")

def netsh_info_to_val(msg):
  return msg.split(":")[1].strip()



class net_rating:
  def __init__(self, strength):
    self.strength = strength
    self.connected_time = 0
    self.num_fails = 0
    log(f" - new net rating, initial strength: {strength}")

  def update_strength(self, strength):
    self.strength = strength
    log(f" - updating net rating's strength: {strength}")

  def register_connected_time(self):
    self.connected_time += 1
    log(f" - updated net rating's connected time: {self.connected_time}")

  def register_fail(self):
    self.num_fails += 1
    log(f" - updated net rating's num fails: {self.num_fails}")

  def get_score(self):
    if self.connected_time == 0:
      score = self.num_fails * -1 
    elif self.num_fails > 0:
      score = self.connected_time / self.num_fails
    else:
      score = self.connected_time #shouldn't ever happen
      
    log(f" - strength:       {self.strength}")
    log(f" - connected time: {self.connected_time}")
    log(f" - num fails:      {self.num_fails}")
    log(f" - score:          {score}")

    return score
  
    # todo: factor in signal strength
    # todo: handle times when there is no network to choose from
    # coulddo: factor in times when we weren't online yet we were connected to the network
  
    

# returns strength int
class net_ratings_mgr:
  def __init__(self):
    self.net_ratings = { }

  def current_strength(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    signal_strs = list()

    for line in interfaces_res:
      if "Signal" in line:
        signal_str = netsh_info_to_val(line)
        signal_strs.append(signal_str)

    if len(signal_strs) == 1:
      strength = signal_strs[0].strip("%")
      strength = int(strength)
      return strength
    elif len(signal_strs) == 0:
      log("error - tried to find signal strength when not connected")
      log("  result of show interfaces cmd:") 
      for line in interfaces_res:
        log(line)
      return -1
    else:
      log("error - multiple signal strength values found")
      log("  result of show interfaces cmd:") 
      for line in interfaces_res:
        log(line)
      return -1

  def update_strength(self, net_id):
    if net_id in self.net_ratings:
      log(f"updating net rating for {net_id}")
      self.net_ratings[net_id].update_strength(self.current_strength())
    else:
      log(f"adding net rating for {net_id}")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})

  def register_connected_time(self, net_id):
    if net_id in self.net_ratings:
      log(f"registering connected time in net rating for {net_id}")
      self.net_ratings[net_id].register_connected_time()
    else:
      log(f"adding net rating for {net_id} to register connected time")
      log("  error - net rating should already exist before registering connected time")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
      self.net_ratings[net_id].register_connected_time()
      
  def register_fail(self, net_id):
    if net_id in self.net_ratings:
      log(f"registering fail in net rating for {net_id}")
      self.net_ratings[net_id].register_fail()
    else:
      log(f"adding net rating for {net_id} to register fail")
      log("  error - net rating should already exist before registering a fail")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
      self.net_ratings[net_id].register_fail()
  
  def choose_best(self, valid_net_ids):

    #1. try networks which haven't yet been tried
    for net_id in valid_net_ids:
      if net_id not in self.net_ratings:
        return net_id

    #2. try network which has had the fewest fails:
    best_net_id = None
    best_score = None
    for net_id in valid_net_ids:
      if net_id in self.net_ratings:
        log(f"getting score for net rating: {net_id}")
        this_score = self.net_ratings[net_id].get_score()
        if (best_net_id == None) or (this_score > best_score):
          best_net_id = net_id
          best_score = this_score

    if best_net_id:
      return best_net_id
    

    
class reconnecter:
  def __init__(self):
    self.current_net_id = ""
    self.net_ratings = net_ratings_mgr()
    self.net_profiles = list()
    
    #getting network profiles on this computer:
    profiles_res = run_proc("netsh wlan show profile")
    profiles_res = profiles_res.split("User profiles")[1]
    profiles_res = parse_cmd_output(profiles_res)
    
    for line in profiles_res:
      if ":" in line:
        profile = netsh_info_to_val(line)
        self.net_profiles.append(profile)
    
    log(f"network profiles found: {self.net_profiles}")

    
    #what is current network connection on startup?:
    if self.am_i_on_wifi():
      self.update_current_net_id()
      log(f"on startup, connected to: {self.current_net_id}")
      self.net_ratings.update_strength(self.current_net_id)
    else:
      log("not connected to a network on startup")

    if self.am_i_online():
      self.previously_online = True
      log("online on startup")
    else:
      self.previously_online = False
      log("not online on startup")
      
  #bool
  def am_i_online(self):
    connected_res = run_proc("amIOnline.bat")
    parsed_1 = connected_res.split("'")[1]
    parsed_2 = parsed_1.split("\\")[0]
    p_res = parsed_2.strip()

    log(p_res)

    if p_res == "online":
      return True
    elif p_res == "not online":
      return False

    return False

  def am_i_on_wifi(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)
    for line in interfaces_res:
      if "Signal" in line:
        return True
    return False
    

  def update_current_net_id(self, given_net_id = None):

    if given_net_id:
      self.current_net_id = given_net_id
      return
    
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    net_ids = list()
    
    for line in interfaces_res:
      if "SSID" in line:
        net_id = netsh_info_to_val(line)
        net_ids.append(net_id)
        
    if len(net_ids) >= 1:
      self.current_net_id = net_ids[0]
    else:
      self.current_net_id = ""

  def reconnect(self):
    nets_res = run_proc("netsh wlan show networks")
    nets_res = parse_cmd_output(nets_res)
    net_ids = list()

    for line in nets_res:
      if "SSID" in line:
        net_id = netsh_info_to_val(line)
        net_ids.append(net_id)

    valid_net_ids = [id for id in net_ids if id in self.net_profiles]

    log(f"valid network ids: {valid_net_ids}")

    best_net_id = self.net_ratings.choose_best(valid_net_ids)
    log(f"attempting to connect to {best_net_id}...")
    connect_cmd = f'netsh wlan connect ssid="{best_net_id}" name="{best_net_id}"'
    connect_res = run_proc(connect_cmd)
    log(connect_res)

    return best_net_id

  def public_loop(self):
    if self.am_i_online():
      if self.previously_online == False:
        if AUDIBLE:
          winsound.PlaySound('./sfx/connected.wav', winsound.SND_FILENAME)
      
      self.net_ratings.register_connected_time(self.current_net_id)

      self.previously_online = True
    else:
      if AUDIBLE:
        print('\a')
        #winsound.PlaySound('./sfx/disconnected.wav', winsound.SND_FILENAME)
      
      if self.current_net_id != "":
        self.net_ratings.register_fail(self.current_net_id)

      if self.am_i_on_wifi():
        run_proc("netsh wlan disconnect")
        
      net_id = self.reconnect()
      sleep(1)
      
      self.update_current_net_id(net_id)
      if self.am_i_on_wifi():
        self.net_ratings.update_strength(self.current_net_id)
      else:
        log("error - just reconnected but not on wifi")

      if not self.am_i_online():
        log("error - just reconnected but not online")

      self.previously_online = False

    return reconnecter_result(connected=self.am_i_on_wifi(), online=self.am_i_online(), current_net_id=self.current_net_id)
  






class MainFrame(wx.Frame):

  def __init__(self, parent):
    wx.Frame.__init__(self, parent, title="Reconnecter")
   
    text_size = wx.Size(36, 20)


    self.panel = wx.Panel(self)
    self.status_label = wx.StaticText(self.panel, size=text_size)
    self.connected_label = wx.StaticText(self.panel, size=text_size)
    self.online_label = wx.StaticText(self.panel, size=text_size)
    self.current_net_id_label = wx.StaticText(self.panel, size=text_size)
    self.start_btn = wx.Button(self.panel, label="start")

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(self.status_label)
    sizer.Add(self.connected_label)
    sizer.Add(self.online_label)
    sizer.Add(self.current_net_id_label)
    
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    button_sizer.Add(self.start_btn)
    sizer.Add(button_sizer)

    self.panel.SetSizerAndFit(sizer)
    self.Bind(wx.EVT_BUTTON, self.Start)

  def Start(self, event):
    self.start_btn.Enable(False)
    self.start_btn.Destroy()

    self.status_label.SetLabel("Running")

    thread = threading.Thread(target=self.main_loop)
    thread.start()

  def main_loop(self):
    r = reconnecter()    
    while True:
      result = r.public_loop()
      wx.CallAfter(self.status_label.SetLabelText,         f"Last update: {result.datetime.strftime('%d/%m/%Y, %H:%M:%S')}")
      wx.CallAfter(self.connected_label.SetLabelText,      f"Connected: {str(result.connected)}")
      wx.CallAfter(self.online_label.SetLabelText,         f"Online: {str(result.online)}")
      wx.CallAfter(self.current_net_id_label.SetLabelText, f"Current Network: {result.current_net_id}")
      sleep(3)

if __name__ == '__main__':
  app = wx.App()
  frame = MainFrame(None)
  frame.Show()
  app.MainLoop()



  
