#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from enum import Enum
import os
from seedemu.core import Node, Service, Server
from typing import Dict, List

import json
from datetime import datetime, timezone

from seedemu.raps.OpenVpnRemoteAccessProvider import OpenVpnRemoteAccessProvider

ETHServerFileTemplates: Dict[str, str] = {}
GenesisFileTemplates: Dict[str, str] = {}

# bootstraper: get enode urls from other eth nodes.
ETHServerFileTemplates['bootstrapper'] = '''\
#!/bin/bash

while read -r node; do {
    let count=0
    ok=true
    until curl -sHf http://$node/eth-enode-url > /dev/null; do {
        echo "eth: node $node not ready, waiting..."
        sleep 3
        let count++
        [ $count -gt 60 ] && {
            echo "eth: node $node failed too many times, skipping."
            ok=false
            break
        }
    }; done

    ($ok) && {
        echo "`curl -s http://$node/eth-enode-url`," >> /tmp/eth-node-urls
    }
}; done < /tmp/eth-nodes
'''

ETHServerFileTemplates['smartcontract'] = '''\
sleep 30
while true
do
    balanceCommand="geth --exec 'eth.getBalance(eth.accounts[0])' attach"
    balance=$(eval "$balanceCommand")
    minimumBalance=1000000
    if [ $balance -lt $minimumBalance ]
    then
        sleep 60
    else
        break
    fi
done
echo "Balance ========> $balance"
gethCommand='{}'
finalCommand='geth --exec "$gethCommand" attach'
result=$(eval "$finalCommand")
touch transaction.txt
echo "transaction hash $result"
echo "$result" >> transaction.txt
'''

GenesisFileTemplates['poa'] = '''\
{
    "config": {
        "chainId": 10,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "clique": {
        "period": 15,
        "epoch": 30000
        }
    },
    "nonce": "0x0",
    "timestamp": "0x622a4e1a",
    "extraData": "0x0",
    "gasLimit": "0x47b760",
    "difficulty": "0x1",
    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {
    },
    "number": "0x0",
    "gasUsed": "0x0",
    "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "baseFeePerGas": null
}
'''

GenesisFileTemplates['pow'] = '''\
{
        "nonce":"0x0",
        "timestamp":"0x621549f1",
        "parentHash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData":"0x",
        "gasLimit":"0x80000000",
        "difficulty":"0x0",
        "mixhash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase":"0x0000000000000000000000000000000000000000",
        "number": "0x0",
        "gasUsed": "0x0",
        "baseFeePerGas": null,
        "config": {
            "chainId": 10,
            "homesteadBlock": 0,
            "eip150Block": 0,
            "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "ethash": {
            }
        },
        "alloc": {
        }
}
'''

class ConsensusMechanism(Enum):
    '''
    @brief Consensus Mechanism Enum. POA for Proof of Authority, POW for Proof Of Work
    '''
    POA = 'poa'
    POW = 'pow'


class Genesis():
    '''
    @brief Genesis manage class
    '''
    __genesis:dict
    __consensusMechaism:ConsensusMechanism
    
    def __init__(self, consensus:ConsensusMechanism):
        self.__consensusMechaism = consensus
        self.__genesis = json.loads(GenesisFileTemplates[self.__consensusMechaism.value]) 

    def setCustomGenesis(self, genesis:str):
        self.__genesis = json.loads(genesis)
    
    def allocateBalance(self, accounts:List[EthAccount]) -> Genesis:
        '''
        @brief allocate balance to account on genesis. It will update the genesis file
        '''
        for account in accounts:
            address = account.getAddress()
            balance = account.getAllocBalance()

            assert balance >= 0, "balance cannot have a negative value. Requested Balance Value : {}".format(account.getAllocBalance())
            if balance != 0:
                self.__genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}

        return self

    def getGenesisBlock(self) -> str:
        '''
        @brief get a json format of genesis block
        
        returns genesis
        '''
        return json.dumps(self.__genesis)

    def setSealer(self, accounts:List[EthAccount]) -> Genesis:
        if len(accounts) > 0: self.__replaceExtraData(self.__generateGenesisExtraData(accounts))
        return self

    def __generateGenesisExtraData(self, prefunded_accounts: List[EthAccount]) -> str:
        '''
        @brief Clique extradata field, used to define PoA validators/sealers must match the following format:
        First part: 32bytes vanity, meaning whatever you want here since it’s expressed as an hex string (64 chars long as one byte is 2 chars), using puppeth tool, it's filled with 0s.
        Second part: concatenated list of sealers/validators nodes addresses. Each address written as hex string without the “0x” prefix and must be 20 bytes long (40 chars long as one byte is 2 chars).
        Third part: a 65 bytes signature suffix called proposer seal. It’s used to identify the proposer of the new validator in a block. Given we talk here about the genesis file, this seal has no reason to be because no specific node proposed it, it’s the base on which everyone agree before starting. So it must be filled with zeros (65 zeros). Puppeth tool puts 130 0s.
        
        @returns the fully generated extraData field for the genesis
        '''

        extraData = "0x" + "0" * 64
        for account in prefunded_accounts:
            extraData = extraData + account.getAddress()[2:]
        
        return extraData + "0" * 130
        
    def __replaceExtraData(self, content:str) -> None:
        assert content != "", "content cannot be a blank."
        self.__genesis["extraData"] = content

    


class EthAccount():
    """
    @brief Ethereum Local Account.
    """

    __address: str    # account address
    __keystore_content: str   # the content of keystore file
    __keystore_filename:str   # the name of keystore file 
    __alloc_balance: int

    def __init__(self, alloc_balance:int = 0,password:str = "admin", keyfile: str = None):
        """
        @brief create a Ethereum Local Account when initialize

        @param alloc_balance the balance need to be alloc
        @param password encrypt password for creating new account, decrypt password for importing account
        @param keyfile content of the keystore file. If this parameter is None, this function will create a new account, if not, it will import account from keyfile
        """
        from eth_account import Account
        self.lib_eth_account = Account
        self.__account = self.__importAccount(keyfile=keyfile, password=password) if keyfile else self.__createAccount()
        self.__address = self.__account.address
        self.__alloc_balance = alloc_balance

        # encrypt private for Ethereum Client, like geth and generate the content of keystore file
        encrypted = self.lib_eth_account.encrypt(self.__account.key, password=password)
        self.__keystore_content = json.dumps(encrypted)

        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        self.__keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]

    
    def __importAccount(self, keyfile: str, password = "admin"):
        """
        @brief import account from keyfile
        """
        print("importing account...")
        assert keyfile is not None, "keyfile cannot be None."
        
        return self.lib_eth_account.from_key(self.lib_eth_account.decrypt(keyfile_json=keyfile,password=password))
    
    def __createAccount(self):
        """
        @brief create account
        """
        print("creating account...")
        return  self.lib_eth_account.create()

    def getAddress(self) -> str:
        return self.__address

    def getAllocBalance(self) -> str:
        return self.__alloc_balance

    def getKeyStoreFileName(self) -> str:
        return self.__keystore_filename

    def getKeyStoreContent(self) -> str:
        return self.__keystore_content


class SmartContract():

    __abi_file_name: str
    __bin_file_name: str

    def __init__(self, contract_file_bin, contract_file_abi):
        self.__abi_file_name = contract_file_abi
        self.__bin_file_name = contract_file_bin

    def __getContent(self, file_name) -> str:
        """!
        @brief get Content of the file_name.

        @param file_name from which we want to read data.
        
        @returns Contents of the file_name.
        """
        file = open(file_name, "r")
        data = file.read()
        file.close()
        return data.replace("\n","")
        

    def generateSmartContractCommand(self):
        """!
        @brief generates a shell command which deploys the smart Contract on the ethereum network.

        @param contract_file_bin binary file of the smart Contract.

        @param contract_file_abi abi file of the smart Contract.
        
        @returns shell command in the form of string.
        """
        abi = "abi = {}".format(self.__getContent(self.__abi_file_name))
        byte_code = "byteCode = \"0x{}\"".format(self.__getContent(self.__bin_file_name))
        unlock_account = "personal.unlockAccount(eth.accounts[0], \"{}\")".format("admin")
        contract_command = "testContract = eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000})"
        display_contract_Info = "testContract"
        finalCommand = "{},{},{},{},{}".format(abi, byte_code, unlock_account, contract_command, display_contract_Info)
        
        return ETHServerFileTemplates['smartcontract'].format(finalCommand)

class EthereumServer(Server):
    """!
    @brief The Ethereum Server
    """

    __id: int
    __is_bootnode: bool
    __no_discover: bool 
    __bootnode_http_port: int
    __geth_http_port: int
    __smart_contract: SmartContract
    __start_Miner_node: bool
    __enable_external_connection: bool
    __unlockAccounts: bool
    __accounts: List[EthAccount]
    __consensus_mechanism: ConsensusMechanism
    __use_custom_geth: bool
    __custom_geth_binary_path: str

    def __init__(self, id: int):
        """!
        @brief create new eth server.

        @param id serial number of this server.
        """
        self.__id = id
        self.__is_bootnode = False
        self.__no_discover = False
        self.__bootnode_http_port = 8088
        self.__geth_http_port = 8545
        self.__smart_contract = None
        self.__start_Miner_node = False
        self.__enable_external_connection = False
        self.__unlockAccounts = False
        self.__accounts = [EthAccount(alloc_balance=32 * pow(10, 18), password="admin")] #create a prefunded account by default. It ensure POA network works when create/import prefunded account is not called.
        self.__consensus_mechanism = ConsensusMechanism.POW

        self.__use_custom_geth = False
        self.__custom_geth_binary_path = None


    def __unlockAccountsCommand(self, node: Node):
        if self.__unlockAccounts:
            """!
            @brief automatically unlocking the accounts in a node.
            Currently used to automatically be able to use our emulator using Remix.
            """

            base_command = "sleep 20\n\
            geth --exec 'personal.unlockAccount(eth.accounts[{}],\"admin\",0)' attach\n\
            "
            
            full_command = ""
            for i in range(len(self.__accounts)):
                full_command += base_command.format(str(i))

            node.appendStartCommand('(\n {})&'.format(full_command))

    def __addMinerStartCommand(self, node: Node):
        if not self.__start_Miner_node:
            """!
            @brief generates a shell command which start miner as soon as it the miner is booted up.
            
            @param ethereum node on which we want to deploy the changes.
            
            """   
            command = " sleep 20\n\
            geth --exec 'eth.defaultAccount = eth.accounts[0]' attach \n\
            geth --exec 'miner.start(1)' attach \n\
            "
            node.appendStartCommand('(\n {})&'.format(command))

    def __deploySmartContractCommand(self, node: Node):
        if self.__smart_contract != None :
            smartContractCommand = self.__smart_contract.generateSmartContractCommand()
            node.appendStartCommand('(\n {})&'.format(smartContractCommand))
    
    def install(self, node: Node, eth: EthereumService, allBootnode: bool):
        """!
        @brief ETH server installation step.

        @param node node object
        @param eth reference to the eth service.
        @param allBootnode all-bootnode mode: all nodes are boot node.
        """

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has not interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        this_url = '{}:{}'.format(addr, self.getBootNodeHttpPort())
        # get other nodes IP for the bootstrapper.
        bootnodes = eth.getBootNodes()[:]
        # if the node itself is a bootnode, remove it from the bootnode list.
        if this_url in bootnodes: bootnodes.remove(this_url)

        # import keystore file to /tmp/keystore
        for account in self.__accounts:
            node.appendFile("/tmp/keystore/"+account.getKeyStoreFileName(), account.getKeyStoreContent())
      
        # We can specify nodes to use a consensus different from the base one
        #####################################
        #  support custom genesis           #
        #####################################

        genesis = Genesis(consensus=self.__consensus_mechanism)

        # update genesis.json
        genesis.allocateBalance(eth.getAllPrefundedAccounts())
        genesis.setSealer(eth.getAllPrefundedAccounts())
    
        node.appendFile('/tmp/eth-genesis.json', genesis.getGenesisBlock())
        node.appendFile('/tmp/eth-nodes', '\n'.join(bootnodes))
        node.appendFile('/tmp/eth-bootstrapper', ETHServerFileTemplates['bootstrapper'])
        node.appendFile('/tmp/eth-password', 'admin') 

        node.addSoftware('software-properties-common')

        # tap the eth repo
        node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')

        # install geth and bootnode
        if self.__use_custom_geth : 
            node.addBuildCommand('apt-get update && apt-get install --yes bootnode')
        else:
            node.addBuildCommand('apt-get update && apt-get install --yes geth bootnode')
            

        # set the data directory
        datadir_option = "--datadir /root/.ethereum"

        # genesis
        node.appendStartCommand('[ ! -e "/root/.ethereum/geth/nodekey" ] && geth {} init /tmp/eth-genesis.json'.format(datadir_option))

        if allBootnode or self.__is_bootnode:
            # generate enode url. other nodes will access this to bootstrap the network.
            # Default port is 30301, you can change the custom port with the next command
            node.appendStartCommand('echo "enode://$(bootnode -nodekey /root/.ethereum/geth/nodekey -writeaddress)@{}:30301" > /tmp/eth-enode-url'.format(addr))
            # Default port is 30301, use -addr :<port> to specify a custom port
            node.appendStartCommand('bootnode -nodekey /root/.ethereum/geth/nodekey -verbosity 9 -addr {}:30301 > /tmp/bootnode-logs &'.format(addr))          
            # host the eth-enode-url for other nodes.
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self.__bootnode_http_port), True)

        # load enode urls from other nodes
        node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
        if not(eth.isManual()):
            node.appendStartCommand('/tmp/eth-bootstrapper')
        
        # launch Ethereum process.
        common_flags = '{} --identity="NODE_{}" --mine --unlock 0 --password "/tmp/eth-password" --networkid=10 --syncmode full --verbosity=2 --allow-insecure-unlock --port 30303 --http --http.addr 0.0.0.0 --http.port {}'.format(datadir_option, self.__id,  self.__geth_http_port)
        
        # Flags updated to accept external connections
        if self.externalConnectionEnabled():
            apis = "web3,eth,debug,personal,net,clique"
            http_whitelist_domains = "*"
            ws_whitelist_domains = "*"
            whitelist_flags = "--http.corsdomain \"{}\" --http.api {} --ws --ws.addr 0.0.0.0 --ws.port {} --ws.api {} --ws.origins \"{}\" ".format(http_whitelist_domains, apis, 8546, apis, ws_whitelist_domains)
            common_flags = '{} {}'.format(common_flags, whitelist_flags)
        
        if self.__no_discover:
            common_flags = '{} {}'.format(common_flags, "--nodiscover")

        # Base geth command
        geth_command = 'nice -n 19 geth {}'.format(common_flags)
        
        # Manual vs automated geth command execution
        # In the manual approach, the geth command is only thrown in a file in /tmp/run.sh
        # In the automated approach, the /tmp/run.sh file is executed by the start.sh (Virtual node) 
        
        # Echoing the geth command to /tmp/run.sh in each container
        node.appendStartCommand('echo \'{} --bootnodes "$(cat /tmp/eth-node-urls)"\' > /tmp/run.sh'.format(geth_command), True) 
       
        # Making run.sh executable
        node.appendStartCommand('sleep 10')
        node.appendStartCommand('chmod +x /tmp/run.sh')
        
        # moving keystore to the proper folder
        for account in self.getAccounts():
            node.appendStartCommand("cp /tmp/keystore/{} /root/.ethereum/keystore/".format(account.getKeyStoreFileName()),True)

        # Adding /tmp/run.sh in start.sh file to automate them
        if not(eth.isManual()):
            node.appendStartCommand('/tmp/run.sh &')

            self.__unlockAccountsCommand(node)
            self.__addMinerStartCommand(node)
            self.__deploySmartContractCommand(node)

        node.appendClassName('EthereumService')
    
    def setCustomGeth(self, customGethBinaryPath:str) -> EthereumServer:
        """
        @brief set custom geth binary file

        @param customGethBinaryPath set abosolute path of geth binary to move to the service.

        @returns self, for chaining API calls
        """

        self.__use_custom_geth = True
        self.__custom_geth_binary_path = customGethBinaryPath

        return self

    def setNoDiscover(self, noDiscover = True) -> EthereumServer:
        """
        @brief setting the automatic peer discovery to true/false
        """
        self.__no_discover = noDiscover
        return self

    def isNoDiscover(self) -> str:
        """
        @brief making sure nodes can automatically discover their peers
        """
        return self.__no_discover


    def setConsensusMechanism(self, consensus:ConsensusMechanism=ConsensusMechanism.POA) -> EthereumServer:
        '''
        @brief We can have more than one consensus mechanism at the same time
        The base consensus (poa) applies to all of the nodes by default except if this API is called
        We can set a different consensus for the nodes of our choice
        '''
        self.__consensus_mechanism = consensus
        
        return self

    def getConsensusMechanism(self) -> ConsensusMechanism:

        return self.__consensus_mechanism

    def getId(self) -> int:
        """!
        @brief get ID of this node.

        @returns ID.
        """
        return self.__id

    def setBootNode(self, isBootNode: bool) -> EthereumServer:
        """!
        @brief set bootnode status of this node.

        Note: if no nodes are configured as boot nodes, all nodes will be each
        other's boot nodes.

        @param isBootNode True to set this node as a bootnode, False otherwise.
        
        @returns self, for chaining API calls.
        """
        self.__is_bootnode = isBootNode

        return self

    def isBootNode(self) -> bool:
        """!
        @brief get bootnode status of this node.

        @returns True if this node is a boot node. False otherwise.
        """
        return self.__is_bootnode

    def setBootNodeHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number hosting the enode url file.

        @param port port

        @returns self, for chaining API calls.
        """

        self.__bootnode_http_port = port

        return self


    def getBootNodeHttpPort(self) -> int:
        """!
        @brief get the http server port number hosting the enode url file.

        @returns port
        """

        return self.__bootnode_http_port

    def setGethHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number for normal ethereum nodes

        @param port port

        @returns self, for chaining API calls
        """
        
        self.__geth_http_port = port
        
        return self

    def getGethHttpPort(self) -> int:
        """!
        @brief get the http server port number for normal ethereum nodes

        @returns int
        """
                
        return self.__geth_http_port


    def enableExternalConnection(self) -> EthereumServer:
        """!
        @brief setting a node as a remix node makes it possible for the remix IDE to connect to the node
        """
        self.__enable_external_connection = True

        return self

    def externalConnectionEnabled(self) -> bool:
        """!
        @brief returns wheter a node is a remix node or not
        """
        return self.__enable_external_connection

    
    def createNewAccount(self, number: int = 1, password: str = "admin", balance: int=0) -> EthereumServer:
        """
        @brief Call this api to create a new account

        @param number the number of prefunded account need to create
        @param balance the balance need to be allocated to the prefunded accounts
        @param password the password of account for the Ethereum client

        @returns self, for chaining API calls.
        """

        for _ in range(number):    
            account = EthAccount(alloc_balance=balance,password=password)
            self.__accounts.append(account)

        return self
    
    def importAccount(self, keyfileDirectory:str, password:str = "admin", balance: int = 0) -> EthereumServer:
        assert keyfileDirectory and os.path.exists(keyfileDirectory), "keyFile does not exist. path : {}".format(keyfileDirectory)

        f = open(keyfileDirectory, "r")
        keystoreFileContent = f.read()
        account = EthAccount(alloc_balance=balance, password=password,keyfile=keystoreFileContent)
        self.__accounts.append(account)
        return self
    
    def getAccounts(self) -> List[EthAccount]:
        """
        @brief Call this api to get the prefunded accounts for this node

        @returns prefunded accounts.
        """

        return self.__accounts

    def unlockAccounts(self) -> EthereumServer:
        """!
        @brief This is mainly used to unlock the accounts in the remix node to make it directly possible for transactions to be 
        executed through Remix without the need to access the geth account in the docker container and unlocking manually

        @returns self, for chaining API calls.
        """
        self.__unlockAccounts = True

        return self
        
    def startMiner(self) -> EthereumServer:
        """!
        @brief Call this api to start Miner in the node.

        @returns self, for chaining API calls.
        """
        self.__start_Miner_node = True

        return self

    def deploySmartContract(self, smart_contract: SmartContract) -> EthereumServer:
        """!
        @brief Call this api to deploy smartContract on the node.

        @returns self, for chaining API calls.
        """
        self.__smart_contract = smart_contract

        return self


class EthereumService(Service):
    """!
    @brief The Ethereum network service.

    This service allows one to run a private Ethereum network in the emulator.
    """

    __serial: int
    __boot_node_addresses: List[str]
    __joined_prefunded_accounts: List[EthAccount]

    __save_state: bool
    __save_path: str
    
    __manual_execution: bool
    __base_consensus_mechanism: ConsensusMechanism

    def __init__(self, saveState: bool = False, manual: bool = False, statePath: str = './eth-states', baseConsensusMechanism:ConsensusMechanism=ConsensusMechanism.POW):
        """!
        @brief create a new Ethereum service.

        @param saveState (optional) if true, the service will try to save state
        of the block chain by saving the datadir of every node. Default to
        false.

        @param manual (optional) if true, the user will have to execute a shell script
        provided in the directory to trigger some commands inside the containers and start
        mining

        @param statePath (optional) path to save containers' datadirs on the
        host. Default to "./eth-states". 
        """

        super().__init__()
        self.__serial = 0
        self.__boot_node_addresses = []
        self.__joined_prefunded_accounts = []

        self.__save_state = saveState
        self.__save_path = statePath

        self.__manual_execution = manual
        self.__base_consensus_mechanism = baseConsensusMechanism

    def getName(self):
        return 'EthereumService'

    def getBootNodes(self) -> List[str]:
        """
        @brief get bootnode IPs.

        @returns list of IP addresses.
        """
        return self.__boot_node_addresses
    
    def isManual(self) -> bool:
        """
        @brief Returns whether the nodes execution will be manual or not

        @returns bool
        """
        return self.__manual_execution
    
    def getAllPrefundedAccounts(self) -> List[EthAccount]:
        """
        @brief Get a joined list of all the created prefunded accounts on all nodes
        
        @returns list of EthAccount
        """
        return self.__joined_prefunded_accounts

    def setBaseConsensusMechanism(self, mechanism:ConsensusMechanism) -> bool:
        """
        @brief select a consensus mechanism for the blockchain network. Default is Proof of authority

        @returns bool
        """
        self.__base_consensus_mechanism = mechanism
        return True

    def getBaseConsensusMechanism(self) -> ConsensusMechanism:
        """
        @returns the consensus mechanism for the current network
        """
        return self.__base_consensus_mechanism

    def _doConfigure(self, node: Node, server: EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())

        if server.isBootNode():
            self._log('adding as{}/{} as bootnode...'.format(node.getAsn(), node.getName()))
            self.__boot_node_addresses.append(addr)

        if len(server.getAccounts()) > 0:
            self.__joined_prefunded_accounts.extend(server.getAccounts())

        if self.__save_state:
            node.addSharedFolder('/root/.ethereum', '{}/{}'.format(self.__save_path, server.getId()))
    
    def install(self, vnode: str) -> EthereumServer:
        """!
        @brief Override function of Sevice.install
        Here is downcasting the return for IntelliSense :)
        """
        return super().install(vnode)

    def _doInstall(self, node: Node, server: EthereumServer):
        self._log('installing eth on as{}/{}...'.format(node.getAsn(), node.getName()))
        
        all_bootnodes = len(self.__boot_node_addresses) == 0

        if all_bootnodes:
            self._log('note: no bootnode configured. all nodes will be each other\'s boot node.')

        server.install(node, self, all_bootnodes)

    def _createServer(self) -> Server:
        self.__serial += 1
        return EthereumServer(self.__serial)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EthereumService:\n'

        indent += 4

        out += ' ' * indent
        out += 'Boot Nodes:\n'

        indent += 4

        for node in self.getBootNodes():
            out += ' ' * indent
            out += '{}\n'.format(node)

        return out
