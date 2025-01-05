
Git Signing Keys
================

As of December 31, 2024 all git tags are signed using key *arch@sapience.com* (openpgp hash 7CCA1BA66669F3273DB52678E5B81343AB9809E1).

We describe how to get and install the signing key to your key ring. Once the key is in the keyring then
git can verify a tag using:

.. code:: bash

    git tag -v [tag-name]


For arch package builders, makepkg does this when using the alternative *source* line
in the PKGBUILD file which is of the form:

.. code:: bash

    source=...#tag=${pkgver}?signed")

To have the git tag verified, simply use this instead of the default which does not end with *signed*.

Getting the Key
---------------

The key is available :

 * on github at https://github.com/gene-git/blog/git-keys

 * on the authors website  https://www.sapience.com/tech

 * For Arch AUR package it is included in the keys/pgp directory.

    NB you will need a fresh copy of the package as older versions did not include the key

 * via WKD 


Installing from Key File
------------------------

The key file for the first three download methods is the usual Openpgp text format (ascii armored version).
To install the file key once you have the file use :

.. code:: bash

    gpg --import [key_file]

for gnupg or

.. code:: bash

    sq key import [key_file]

for sequoia.


Installing via WKD
------------------

Web Key directory (WKD) has come to replace the older and to be avoided pgp servers.

The old pgp key servers suffer a *key* (🤔) design flaw that allows anyone to upload a key claiming
to be any person/email. The assumption was that whoever downloaded the key would find a different
way to verify the key. Clearly, pgp keyservers do not present a robust methodology. 

WKD has the benefit that that the key is available from the same domain as the email ID of the key
and it is therefore reasonable to hold a higher degree of initial trust in the 
website which is the same domain as the key owner's email.

Both gpg and sequioa support dowloading the key directly via WKD. However we have found that tools built
on gnutls, like gpg, can sometimes fail to correctly handshake with more modern, high security
websites. We provide a simple work around for this case.

To install directly when using sequoia:

.. code:: bash

    sq network wkd search arch@sapience.com

and using gpg we recommend simply avoiding their builtin web server library and instead

.. code:: bash

    curl $(gpg-wks-client --print-wkd-url arch@sapience.com) | gpg --import


This works fine provided curl is built against openssl (or other non-gnutls library) [debian-curl]_. 

The *gpg-wks-client* part of the command, prints the WKD server URL of the key. In WKD, the url where
the key is available is generated from the username part of the email address. Also, 
please note that the WKD key is not ascii armored.

You can also run *gpg-wks-client --print-wkd-url arch@sapience.com* and use a browser
with that URL to download the key file if you so choose.


.. [debian-curl] Debian users may find curl is built against gnutls. Can use browser in this case.



