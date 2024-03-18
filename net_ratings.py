from logger import log
from utils import *

class net_rating:
  def __init__(self, strength):
    self.strength = strength
    self.connected_time_since_startup = 0
    self.connected_time_since_reconnect = 0
    self.num_fails = 0
    self.fail_timestamps = []
    log(f" - new net rating, initial strength: {strength}")

  def update_strength(self, strength):
    self.strength = strength
    log(f" - updating net rating's strength: {strength}")

  def register_connected_time(self, seconds_between_pings):
    self.connected_time_since_startup += seconds_between_pings
    self.connected_time_since_reconnect += seconds_between_pings  
    log(f" - updated net rating's connected time since startup:   {self.connected_time_since_startup}")
    log(f" - updated net rating's connected time since reconnect: {self.connected_time_since_reconnect}")

  def register_fail(self):
    self.num_fails += 1
    log(f" - updated net rating's num fails: {self.num_fails}")
    self.connected_time_since_reconnect = 0
    self.fail_timestamps.append(datetime.now())

  def get_score(self):
    connected_time = self.connected_time_since_startup 
    if connected_time == 0:
      score = self.num_fails * -1 
    elif self.num_fails > 0:
      score = connected_time / self.num_fails
    else:
      score = connected_time #shouldn't ever happen
      
    log(f" - strength:                         {self.strength}")
    log(f" - connected time (since startup):   {seconds_to_hours(self.connected_time_since_startup)}")
    log(f" - connected time (since reconnect): {seconds_to_hours(self.connected_time_since_reconnect)}")
    log(f" - num fails:                        {self.num_fails}")
    log(f" - score:                            {score}")

    return score
  
    # todo: factor in signal strength
    # todo: handle times when there is no network to choose from
    # coulddo: factor in times when we weren't online yet we were connected to the network
  
    

# returns strength int
class net_ratings_mgr:
  def __init__(self, seconds_between_pings):
    self.seconds_between_pings = seconds_between_pings
    self.net_ratings = { }

  def current_strength(self):
    interfaces_res = run_proc("netsh wlan show interfaces")
    interfaces_res = parse_cmd_output(interfaces_res)

    signal_strs = []

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
      self.net_ratings[net_id].register_connected_time(self.seconds_between_pings)
    else:
      log(f"adding net rating for {net_id} to register connected time")
      log("  error - net rating should already exist before registering connected time")
      self.net_ratings.update({net_id : net_rating(self.current_strength())})
      self.net_ratings[net_id].register_connected_time(self.seconds_between_pings)
      
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