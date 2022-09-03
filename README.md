# RPKI updates 09/02:

### To deploy RPKI:
- You need to specify one host for RPKI within an AS. The hostname must include `rpki` in the naming. A custom IP is needed in this form `10.asn.0.71`.  

### Here is an example:
```
as150.createHost('host_rpki').joinNetwork('net0', address = '10.150.0.71')
```
- A03-real-world is an edited ready-to-run example.
- By doing the above the RPKI validator should be installed and the RTR port listening on port 3323.
- You can check the status of the rpki using this command in birdc: 'show protocol all rpki'
- You can check `/var/log/bird.log` for debugging.
- This modification implements the best case scenario, where all ASs has a rpki validator implemented. You can reconfigure the router `/etc/bird/bird.conf` to route without using RPKI.

### The changes done on the .py files are:

- The connection to the real internet - `/seedemu/core/Node.py` line `1037 and 1045`.
- The validator installation and RTR server setup - `/seedemu/compiler/Docker.py` line `25-26`, and `865-887`.
- Bird configuration - `/seedemu/layers/Ebgp.py` line `41-82`, `146`, and `161-206`. 
- If there is an issue, it's more likely due to the configuration.

### To test RPKI - you can use the following to hijack a prefix.
```
protocol static hijacks {
    ipv4 {
        table t_bgp;
    };
    route 74.80.186.0/25 blackhole   { bgp_large_community.add(LOCAL_COMM); };
    route 74.80.186.128/25 blackhole { bgp_large_community.add(LOCAL_COMM); };
}
```

### Next Step:
- [krill](https://krill.docs.nlnetlabs.nl/en/stable/testbed.html) implementation: to create a local Trust Anchor Locator (TAL)

--------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------
Internet Emulator
---

The objective of the SEED-Emulator project is to help create emulators of
the Internet. These emulators are for educational uses, and they can be
used as the platform for designing hands-on lab exercises for various subjects,
including cybersecurity, networking, etc.

The project provides essential elements of the Internet (as Python classes), including
Internet exchanges, autonomous systems, BGP routers, DNS infrastructure,
a variety of services. Users can use these elements as the building blocks
to build their emulation programmatically. The output of the program
is a set of docker container folders/files. When these containers are built and
started, they form a small-size Internet. New building blocks are being added,
including Blockchain, Botnet, and many other useful elements of the Internet.

![The Web UI](docs/assets/web-ui.png)

## Table of Contents

-  [Getting Started](#getting-started)
-  [Documentation](#documentation)
-  [Contributing](#contributing)
-  [License](#license)


## Getting Started

To get started with the emulator, install docker, docker-compose, and python3. Then, take a look at the [examples/](./examples/) folder for examples. Detailed explanation is provided in the README file, as well as in the comments of the code. To run an example:

1. Pick an example, say `A00-simple-peering`.
2. Add `seedemu` to `PYTHONPATH`. This can be done by running `source development.env` under the project root directory.
3. Build the emulation. For this example, cd to `examples/A00-simple-peering/`, and run `python3 ./simple-peering.py`. The container files will be created inside the `output/` folder. For some examples, such as `B02-mini-internet-with-dns`, they depend on other examples, so you need to run those examples first. This is part of our component design.
4. Build and run the containers. First `cd output/`, then do `docker-compose build && docker-compose up`. The emulator will start running. Give it a minute or two (or longer if your emulator is large) to let the routers do their jobs.
5. Optionally, start the seedemu web client. Open a new terminal window, navigate to the project root directory, cd to `client/`, and run `docker-compose build && docker-compose up`. Then point your browser to http://127.0.0.1:8080/map.html, and you will see the entire emulator. Use the filter box if you want to see the packet flow.

## Documentation

Documentation is in progress inside the [docs/](./docs/) folder.

## Contributing

Contributions to SEED-Emulator are always welcome. For contribution guidelines, please see [CONTRIBUTING](./CONTRIBUTING.md).

## License

The software is licensed under the GNU General Public License v3.0 license, with copyright by The SEED-Emulator Developers (see [LICENSE](./LICENSE.txt)).
