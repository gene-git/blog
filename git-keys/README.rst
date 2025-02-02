
Git Signing Keys
================

As of December 31, 2024 all git tags are signed by our *arch@sapience.com* signing key.

To install the signing key to your key ring it can be downloaded directly or by using
Web Key directory (WKD). 

After the key is in your keyring then git can verify the source with a tag using:

.. code:: bash

    git tag -v [tag-name]


For arch package builders, makepkg can verify the git tag by using the alternative *source* line
provided in the PKGBUILD file which is of the form:

.. code:: bash

    source=...#tag=${pkgver}?signed")

The *?signed* is what triggers the git tag verification.
Simply use this instead of the default source line, which does not end with *signed*, and 
makepkg will then verify the source code.

Getting the Key
---------------

The key has an openpgp ID hash of *7CCA1BA66669F3273DB52678E5B81343AB9809E1* 
and is available from our website
`arch@sapience.com <https://www.sapience.com/keys/arch-7CCA1BA66669F3273DB52678E5B81343AB9809E1.pub.asc>`_

* On github at `git-keys <https://github.com/gene-git/blog/tree/master/git-keys">`_
* The Arch AUR package has the key included in the keys/pgp directory.
  (Get a fresh copy of package)
* Using WKD

Installing from Key File
------------------------

The key is an OpenPGP public key, and beside for the WKD file which is binary, it
is in the standard OpenPGP ascii armored text format.

To install the key into your keyring once you have the file use :

.. code:: bash

    gpg --import [key_file]

for gnupg or

.. code:: bash

    sq key import [key_file]

for sequoia.


Installing via WKD
------------------

Web Key directory (WKD) has replaced the older and to be avoided pgp servers.

The old pgp key servers suffer a *key* (🤔) design flaw that allows anyone to upload a key claiming
to be any person/email. The assumption was that whoever downloaded the key would find some other
way to verify the key. Clearly, pgp keyservers do not present a robust methodology. 

In contrast, WKD has the benefit that the key is available from the website of the same domain 
as the key owners email ID and it is therefore quite reasonable that this approach offers 
a higher degree of initial trust.

Both gpg and sequoia support dowloading the key directly via WKD. However we have found that tools built
on gnutls, like gpg, can sometimes fail to correctly handshake with more modern, high security
websites. We provide a simple work around for this case.

To install directly when using sequoia:

.. code:: bash

    sq network wkd search arch@sapience.com

and using gpg we recommend simply avoiding their builtin web server access methods and instead use:

.. code:: bash

    curl $(gpg-wks-client --print-wkd-url arch@sapience.com) | gpg --import

This works provided curl is built against openssl (or other non-gnutls library) [1]_. 

The *gpg-wks-client* part of the command, prints the WKD server URL of the key. In WKD, the url where
the key is available is generated from the username part of the email address. Also, 
please note that the WKD key is not ascii armored.

You can also run *gpg-wks-client --print-wkd-url arch@sapience.com* and use a browser
with that URL to download the key file if you so choose.


.. [1] Debian users may find curl is built against gnutls. Can use browser in this case.



