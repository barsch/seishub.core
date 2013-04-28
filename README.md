[![Build Status](https://secure.travis-ci.org/barsch/seishub.core.png?branch=master)](https://travis-ci.org/barsch/seishub.core)

Welcome to SeisHub
==================

Summary
-------

Seismic databases and processing tools currently available are mainly limited to classic three-component seismic recordings and cannot handle collocated multi-component, multi-disciplinary datasets easily. Further, these seismological databases depend on event-related data and are not able to manage state of the art continuous waveform data input as well. None of them allows for automated request of data available at seismic data centers or to share specific data to users outside one institute. Some seismic databases even depend on licensed database engines, which contradicts the open source character of most software packages used in seismology.

This study intends to provide a suitable answer to the deficiencies of existing seismic databases. SeisHub is a novel web-based database approach created for archiving, processing, and sharing geophysical data and meta data (data describing data), particularly adapted for seismic data. The implemented database prototype offers the full functionality of a native XML database combined with the versatility of a RESTful Web service. The XML database itself uses a standard relational database as back-end, which is currently tested with [PostgreSQL](http://www.postgres.org/) and [SQLite](http://www.sqlite.org/). This sophisticated structure allows for the usage of both worlds: on the one hand the power of the SQL for querying and manipulating data, and one the other hand the freedom to use any standard connected to XML, e.g. document conversion via XSLT (Extensible Stylesheet Language Transformations) or resource validation via XSD (XML Schema). The actual resources and any additional services are available via fixed Uniform Resource Identifiers (URIs), where as the database back-end stores the original XML documents and all related indexed values. Indexes are generated using the XPath language and may be added at any time during runtime. This flexibility of the XML/SQL mixture introduced above enables the user to include parameters or results as well as meta data from additional or yet unknown monitoring techniques at any time. SeisHub also comprises features of a “classical seismic database” providing direct access to continuous seismic waveform data and associated meta data. Additionally, SeisHub offers various access protocols (HTTP/HTTPS, SFTP, SSH), an extensible plug-in system, user management, and a sophisticated web-based administration front-end. The SeisHub database is an open source project and can be freely downloaded via the project home page http://www.seishub.org.

The SeisHub database has already been deployed as central database component within two scientific projects: [Exupéry](http://www.exupery-vfrs.de/), a mobile Volcano Fast Response System (VFRS), and BayernNetz, the seismological network of the Bavarian Seismological Service [Erdbebendienst Bayern](http://www.erdbeben-in-bayern.de/).
Acknowledgements

This project was funded by the German Science Foundation (DFG) via grant DFG IG 16/9-1.

Documentation
-------------

* Barsch, Robert (2009): [Web-based technology for storage and processing of multi-component data in seismology: First steps towards a new design](http://edoc.ub.uni-muenchen.de/11043/). Dissertation, LMU München: Fakultät für Geowissenschaften.
* A tutorial for writing SeisHub Plugins: [seishub.plugins.how_to_extend_seishub](https://github.com/krischer/seishub.plugins.how_to_extend_seishub)

###### Related Papers ######

* Bernsdorf, S., Barsch, R., Beyreuther, M., Zakšek, K., Hort, M., Wassermann, J. (2010), [Decision support system for the mobile volcano fast response system](http://www.tandfonline.com/toc/tjde20/3/3). International Journal of Digital Earth. 3 (3), 280-291.
* Beyreuther, M., Barsch, R., Krischer, L., Megies, T., Behr, Y., and Wassermann, J. (2010), [ObsPy: A Python Toolbox for Seismology](http://www.seismosoc.org/publications/SRL/SRL_81/srl_81-3_es/), Seismological Research Letters, 81 (3), 530-533.
* Megies, T., Beyreuther, M., Barsch, R., Krischer, L., and Wassermann, J. (2011), [ObsPy - What can it do for data centers and observatories?](http://www.annalsofgeophysics.eu/index.php/annals/article/view/4838), Annals of Geophysics, 54 (1).

Installing SeisHub
------------------

The following section shows how to install SeisHub and associated components. It will not cover the installation of a relational database back-end, like [PostgreSQL](http://www.postgresql.org/). Please refer to the manual of the preferred database.

For Linux and UNIX systems the author suggests to install !SeisHub as a non-administrative user applying a new, separate, local Python >= 2.6.x instance.

Installing Python on a Windows operating system is more complicated because development tools like a C compiler are not part of a standard Windows distribution. Therefore many Python modules using C extensions have to be delivered as binary package with an executable installer. The fastest, most unproblematic way is to install Python and all extensions as the administrative system user.


### Python ###

1. Download and uncompress the latest stable Python 2.6.x package for the used operating system from http://www.python.org/download/. Windows user may just use the executable installer and skip to the next subsection.
2. Run 

        ./configure --prefix=$HOME
        make
        make install

3. Add `$HOME/bin` to the `PATH` environmental variable, e.g. in bash:

        export PATH="$HOME/bin:$PATH"

4. Call `python` in command line. It should show the correct version number.


### Easy Install ###

Easy Install is a powerful command-line based package management tool for Python. Like CPAN for Perl, it automates the download, build, installation and update process of Python packages.

1. Download http://python-distribute.org/distribute_setup.py.
2. Run 

        python distribute_setup.py

### Required Python extensions ###

    easy_install SQLAlchemy
    easy_install Cheetah
    easy_install pycrypto
    easy_install Twisted
    easy_install pyparsing
    easy_install pyasn1
    easy_install lxml               # Linux requires libxml2-dev and libxslt-dev
    easy_install pyOpenSSL          # Linux requires libssl-dev
    easy_install numpy              # see link in Notes
    easy_install obspy

The [seismology plug-in](https://github.com/barsch/seishub.plugins.seismology) requires the following additional modules:

    easy_install matplotlib

###### Notes ######

* More details (especially for *matplotlib* and *numpy* installation on linux) can be found at https://github.com/obspy/obspy/wiki/Installation-on-Linux:-Dependencies
* Windows users need to install *pywin32* (Python for Windows extension). Download and install from http://sourceforge.net/projects/pywin32/.
* Package *lxml* requires the *libxml2-dev* and *libxslt-dev* packages. Compiling takes a while. This does not apply to an installation on Windows - here are binaries delivered.
* Binary packages for *pyOpenSSL* can be found at http://www.egenix.com/products/python/pyOpenSSL/ or http://sourceforge.net/projects/pyopenssl/


### Additional database bindings (optional) ###

SeisHub uses as default data back-end [SQLite](http://www.sqlite.org/), which comes with Python 2.6.x. 

For [PostgreSQL](http://www.postgresql.org/) additional database bindings are required. Those bindings can be installed via:

    easy_install psycopg2           # Linux requires libpq-dev

###### Notes ######
* On Debian/Ubuntu install *python-psycopg2* via package management
* Windows binary packages for *psycopg2* can be found at http://www.stickpeople.com/projects/python/win-psycopg/

### SeisHub ###

1. Get the latest SeisHub version via PyPI
        
        easy_install seishub.core==dev

2. Optionally get any plug-in you need, e.g.:

        easy_install seishub.plugins.seismology==dev

3. Go into your Python script directory and initialize a new local instance:
        
        seishub-admin initenv /path/to/instance

4. Change to the bin directory within the instance path and start the server

        cd /path/to/instance/bin
        ./start.sh

5. Open http://localhost:8080/manage in your browser. Default user name and password are both set to "admin".
 
You probably want to stop the server after the first run and adjust the
settings within the configuration file `seishub.ini` within the `conf`
directory or use the web interface for that.

### PostgreSQL (optional) ###

Using PostgreSQL as default database backend requires a few more additional steps:

1. Login as postgres super user

        su - postgres

2. Create a new database user "username" using [`createuser`](http://developer.postgresql.org/pgdocs/postgres/app-createuser.html). It will prompt for a password.

        createuser -D -P -S -R username

3. Create a new database "databasename" for the user "username" using [`createdb`](http://developer.postgresql.org/pgdocs/postgres/app-createdb.html).

        createdb -O username databasename

4. Logout

After creating the user and database you may use the connection string `postgresql://username:password@host:port/databasename` (postgres default port is `5432`).
