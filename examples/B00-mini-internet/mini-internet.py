#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from seedemu.raps import OpenVpnRemoteAccessProvider
from seedemu.utilities import Makers
from typing import List, Tuple, Dict
import argparse
import random


# Process command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', type=int, required = False,
                    help="RPKI deployment percentage")
FLAGS = parser.parse_args()

###############################################################################
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
ovpn    = OpenVpnRemoteAccessProvider()

###############################################################################
ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix102 = base.createInternetExchange(102)
ix103 = base.createInternetExchange(103)
ix104 = base.createInternetExchange(104)
ix105 = base.createInternetExchange(105)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('NYC-100')
ix101.getPeeringLan().setDisplayName('San Jose-101')
ix102.getPeeringLan().setDisplayName('Chicago-102')
ix103.getPeeringLan().setDisplayName('Miami-103')
ix104.getPeeringLan().setDisplayName('Boston-104')
ix105.getPeeringLan().setDisplayName('Huston-105')

###############################################################################
# 5 Transit ASes -> 100-105
# 12 Stub ASes -> 106-117
# Total num ASes of 17
total_ASes =  17
if FLAGS.d:       
  dep_percentage = FLAGS.d/100
  true_count = int(total_ASes * dep_percentage)
  false_count = total_ASes - true_count
  rpki = [True] * true_count + [False] * false_count
  #random.seed(0) 
  random.shuffle(rpki)
else: # no percentage specified, do not deploy RPKI
  rpki = [False] * total_ASes
  
###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
Makers.makeTransitAs(base, 2, [100, 101, 102, 105],
       [(100, 101), (101, 102), (100, 105)], rpki[0]
)

Makers.makeTransitAs(base, 3, [100, 103, 104, 105], 
       [(100, 103), (100, 105), (103, 105), (103, 104)], rpki[1]
)

Makers.makeTransitAs(base, 4, [100, 102, 104], 
       [(100, 104), (102, 104)], rpki[2]
)

## Tier 2 ASes
Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)], rpki[3])
Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)], rpki[4])

###############################################################################
# Create single-homed stub ASes. "None" means create a host only 
# The /layers/EBgp.py check if the router hase rpki in the name to apply the rpki bird configuration
Makers.makeStubAs(emu, base, 106, 100, [None], rpki[5])
Makers.makeStubAs(emu, base, 107, 100, [None], rpki[6])

Makers.makeStubAs(emu, base, 108, 101, [None], rpki[7])
Makers.makeStubAs(emu, base, 109, 101, [None], rpki[8])

Makers.makeStubAs(emu, base, 110, 102, [None], rpki[9])

Makers.makeStubAs(emu, base, 111, 103, [None], rpki[10])
Makers.makeStubAs(emu, base, 112, 103, [None], rpki[11])
Makers.makeStubAs(emu, base, 113, 103, [None], rpki[12])

Makers.makeStubAs(emu, base, 114, 104, [None], rpki[13])
Makers.makeStubAs(emu, base, 115, 104, [None], rpki[14])

Makers.makeStubAs(emu, base, 116, 105, [None], rpki[15])
Makers.makeStubAs(emu, base, 117, 105, [None], rpki[16])

# Create real-world AS.
# AS11872 is the Syracuse University's autonomous system

as11872 = base.createAutonomousSystem(11872)
as11872.createNetwork('net0')
as11872.createRealWorldRouter('rw_rpki').joinNetwork('ix102', '10.102.0.118').joinNetwork('net0')

#host_addr = '10.{}.0.74'.format(asn)
as11872.createHost('host_rpki').joinNetwork('net0')

# Allow outside computer to VPN into AS-108's network
as108 = base.getAutonomousSystem(108)
as108.getNetwork('net0').enableRemoteAccess(ovpn)


###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer,
# which means each AS will only export its customers and their own prefixes.
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others.

ebgp.addRsPeers(100, [2, 3, 4])
ebgp.addRsPeers(102, [2, 4])
ebgp.addRsPeers(104, [3, 4])
ebgp.addRsPeers(105, [2, 3])

# To buy transit services from another autonomous system,
# we will use private peering

ebgp.addPrivatePeerings(100, [2],  [106, 107], PeerRelationship.Provider)
ebgp.addPrivatePeerings(100, [3],  [106], PeerRelationship.Provider)

ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [12], [108, 109], PeerRelationship.Provider)

ebgp.addPrivatePeerings(102, [2, 4],  [11, 110], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [11], [110, 11872], PeerRelationship.Provider)

ebgp.addPrivatePeerings(103, [3],  [111, 112, 113], PeerRelationship.Provider)

ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [4],  [114], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [12], [115], PeerRelationship.Provider)

ebgp.addPrivatePeerings(105, [3],  [11, 116], PeerRelationship.Provider)
ebgp.addPrivatePeerings(105, [11], [117], PeerRelationship.Provider)


###############################################################################

# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

# Save it to a component file, so it can be used by other emulators
emu.dump('base-component.bin')

# Uncomment the following if you want to generate the final emulation files
emu.render()
emu.compile(Docker(), './output')

