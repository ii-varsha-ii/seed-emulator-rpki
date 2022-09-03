## RPKI updates 09/02:

To deploy RPKI:
- You need to specify one host for RPKI within an AS - the host name must include rpki in the naming. A custom IP is needed in `10.asn.0.71`.
Here is an example:
```
as150.createHost('host_rpki').joinNetwork('net0', address = '10.150.0.71')
```
- By doing the above the RPKI validator should be installed and the RTR port listening on port 3323.
- The second step is the bird configuration. Instead of of using Ebgp for peering, use E
## Issues with Bird configuration:

- The bird configuration file is on `/etc/bird/bird.conf`
- Here are the changes I made to bird.conf as the [bird documentation](https://bird.network.cz/?get_doc&v=20&f=bird-6.html#ss6.13) suggested.
```
roa4 table r4;
roa6 table r6;

protocol rpki {
        roa4 { table r4; };
        roa6 { table r6; };

        remote 10.150.0.71 port 3323
        retry keep 5;
        refresh keep 30;
        expire 600;

}

filter peer_in_v4 {
        if (roa_check(r4, net, bgp_path.last) = ROA_INVALID) then
        {
                print "Ignore RPKI invalid ", net, " for ASN ", bgp_path.last;
                reject;
        }
        accept;
}
```
- When trying to import a filter, I got this error that I could not fix: `syntax error, unexpected CF_SYM_UNDEFINED`.

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
