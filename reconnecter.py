from subprocess import Popen
import subprocess
from time import sleep
import datetime

VERBOSE = True

#logging:
log_file_name = "reconnecter" + str(datetime.datetime.now()) + ".log"
log_file_name = log_file_name.replace(" ", "-")
log_file_name = log_file_name.replace(":", "-")

def log(msg):
  with open(log_file_name, "a") as log_f:
    now_str = str(datetime.datetime.now())
    log_str = f"{now_str}: {msg}"
    log_f.write(log_str)
    log_f.write('\n\n')

    if VERBOSE:
      print(log_str)


      
#util functions:
def run_proc(cmd):
  p = Popen(cmd, stdout=subprocess.PIPE)
  p_out, p_err = p.communicate()
  return str(p_out)

# parses command output for netsh commands - NOT batch file's echo output
def parse_cmd_output(msg):
  return msg.split("\\r\\n")

def netsh_info_to_net_id(msg):
  return msg.split(":")[1].strip()




class net_rating:
  def __init__(self, strength):
    self.num_fails = 0
    self.strength = strength
    log(f" - new net rating, initial strength: {strength}")

  def update_strength(self, strength):
    self.strength = strength
    log(f" - updating net rating's strength: {strength}")
    
  def register_fail(self):
    self.num_fails += 1
    log(f" - updated net rating's num fails: {self.num_fails}")


# returns strength int
class net_ratings_mgr:
  def __init__(self):
    self.net_ratings = { }

  def current_strength(self):
    inters_res = run_proc("netsh wlan show interfaces")
    inters_res = parse_cmd_output(inters_res)

    signal_strs = list()

    for line in inters_res:
      if "Signal" in line:
        signal_str = netsh_info_to_net_id(line)
        signal_strs.append(signal_str)

    if len(signal_strs) == 1:
      strength = signal_strs[0].strip("%")
      strength = int(strength)
      return strength
    else:
      log("error - multiple signal strength values found")
      return -1

  def update_strength(self, net_id):
    if net_id in self.net_ratings:
      log(f"updaing net rating for {net_id}")
      self.net_ratings[net_id].update_strength(self.current_strength())
    else:
      log(f"adding net rating for {net_id}")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
  
  def register_fail(self, net_id):
    if net_id in self.net_ratings:
      log(f"updaing net rating for {net_id}")
      self.net_ratings[net_id].register_fail()
    else:
      log(f"adding net rating for {net_id}")
      log("error - a net should have been found for registering a fail")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
      self.net_ratings[net_id].register_fail()
  
  def choose_best(self, valid_net_ids):

    #1. try networks which haven't yet been tried
    for net_id in valid_net_ids:
      if net_id not in self.net_ratings:
        return net_id

    #2. try network which has had the fewest fails:
    best_net_id = None
    fewest_fails = None
    for net_id in valid_net_ids:
      if net_id in self.net_ratings:
        if (best_net_id == None) or (self.net_ratings[net_id].num_fails < fewest_fails):
          best_net_id = net_id
          fewest_fails = self.net_ratings[net_id].num_fails

          
    return best_net_id
        
    # todo: factor in signal strength











   




class reconnecter:
  def __init__(self):
    self.current_net_id = ""
    self.net_ratings = net_ratings_mgr()
    self.profiles = list()
    
    #getting network profiles on this computer:
    profiles_res = run_proc("netsh wlan show profile")
    profiles_res = profiles_res.split("User profiles")[1]
    profiles_res = parse_cmd_output(profiles_res)
    
    for line in profiles_res:
      if ":" in line:
        profile = netsh_info_to_net_id(line)
        self.profiles.append(profile)
    
    log(f"network profiles found: {self.profiles}")

    
    #what is current network connection?:
    if self.am_i_connected():
      self.update_current_net_id()
      log(f"on startup, connected to: {self.current_net_id}")
      self.net_ratings.update_strength(self.current_net_id)
    else:
      log("not connected to a network on startup")
      
  #bool
  def am_i_connected(self):
    connected_res = run_proc("amIConnected.bat")
    parsed_1 = connected_res.split("'")[1]
    parsed_2 = parsed_1.split("\\")[0]
    p_res = parsed_2.strip()

    log(p_res)

    if p_res == "connected":
      return True
    elif p_res == "not connected":
      return False

    return False

  def update_current_net_id(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    net_ids = list()
    
    for line in interfaces_res:
      if "SSID" in line:
        net_id = netsh_info_to_net_id(line)
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
        net_id = netsh_info_to_net_id(line)
        net_ids.append(net_id)

    valid_net_ids = [id for id in net_ids if id in self.profiles]

    log(f"valid network ids: {valid_net_ids}")

    best_net_id = self.net_ratings.choose_best(valid_net_ids)
    log(f"attempting to connect to {best_net_id}...")
    connect_cmd = f'netsh wlan connect ssid="{best_net_id}" name="{best_net_id}"'
    connect_res = run_proc(connect_cmd)
    log(connect_res)


  def public_loop(self):
    if self.am_i_connected():
      pass
    else:
      print('\a')
      if self.current_net_id != "":
        self.net_ratings.register_fail(self.current_net_id)
      self.reconnect()
      self.update_current_net_id()
      self.net_ratings.update_strength(self.current_net_id)

  

#main code:
reconnecter = reconnecter()
while True:
  reconnecter.public_loop()
  sleep(3)
