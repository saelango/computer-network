# Final Skeleton

from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class Final (object):
  """
  A Firewall object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

  def do_final (self, packet, packet_in, port_on_switch, switch_id):
    def send_packet(packet, packet_in, port_out):
       table = of.ofp_flow_mod()
       table.match = of.ofp_match.from_packet(packet)
       table.idle_timeout = 30
       table.hard_timeout = 30
       table.buffer_id = packet_in.buffer_id
       table.actions.append(of.ofp_action_output(port=port_out))
       self.connection.send(table)

    def drop_packet(packet, packet_in):
        table = of.ofp_flow_mod()
        table.match = of.ofp_match.from_packet(packet)
        table.idle_timeout = 30
        table.hard_timeout = 30
        table.buffer_id = packet_in.buffer_id
        self.connection.send(table)

    dept_a = ['128.114.1.101', '128.114.1.102', '128.114.1.103', '128.114.1.104']
    dept_b = ['128.114.2.201', '128.114.2.202', '128.114.2.203', '128.114.2.204']

    ip = packet.find('ipv4')
    if ip is not None:
        # untrusted host can't send any IP traffic to the server
        if ip.srcip == "108.35.24.113" and ip.dstip == "128.114.3.178":
            drop_packet(packet, packet_in)
            return
        # trusted host can't send any IP traffic to the server
        elif ip.srcip == "192.47.38.109" and ip.dstip == "128.114.3.178":
            drop_packet(packet, packet_in)
            return

    icmp = packet.find('icmp')
    if icmp is not None:
        # untrusted can't send ICMP traffic to hosts/server
        if ip.srcip == "108.35.24.113" and (ip.dstip in dept_a or ip.dstip in dept_b or ip.dstip == "128.114.3.178"):
            drop_packet(packet, packet_in)
            return
        # trusted can't send ICMP traffic to dept b or server
        elif ip.srcip == "192.47.38.109" and (ip.dstip in dept_b or ip.dstip == "128.114.3.178"):
            drop_packet(packet, packet_in)
            return
        # blocking ICMP traffic between dept a and dept b
        elif (ip.srcip in dept_a and ip.dstip in dept_b) or (ip.srcip in dept_b and ip.dstip in dept_a):
            drop_packet(packet, packet_in)
            return

    # Forward packet (do after dropping packets)
    msg = of.ofp_flow_mod()
    msg.match = of.ofp_match.from_packet(packet)
    msg.idle_timeout = 30
    msg.hard_timeout = 30
    msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
    msg.data = packet_in
    self.connection.send(msg)

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.
    self.do_final(packet, packet_in, event.port, event.dpid)

def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Final(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
