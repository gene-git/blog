.. SPDX-License-Identifier: MIT


Dual Root Capable Linux System
==============================
AKA hot spare alternate root disk
---------------------------------

The goal is have a system with two separate boot disks, each with the same software installed
and kept in sync with one another. 
In the event of a root disk failure, the alternate root disk can be quickly deployed.
We expect that the UEFI bios will boot the alternate root disk if the first one is 
unavailable - but one can always use the bios boot menu, the one that lets user choose which drive to
boot, where both root disks should be offered. 

I should point out, this is something that is easy to add to any existing machine
that can provide the disk space. And the alternate disk can be any size as long as there is
enough space to do the job.  

The downtime is only long enough to add an SSD or hard drive,
the rest is done while computer is up and running normally.

The assumed starting point is a working linux computer using systemd-boot. We use Archlinux
but the distro shouldn't play any significant role in dual root setup. 
We find the Arch rolling release distro convenient and robust.

A frequent question is why not just use RAID-1. The short answer is it's not simple to 
have the <esp> in the raid. While it is doable, it seems hacky and brittle to me, and as one
person put it even bootctl wont work. See the bottom of this note for a link to
a mailing list discussion that touches on this.

The best way to do things, in my view, is to use RAID for dynamic data such as mail or databases
and use dual root for the more stable things like <esp>, /bootm, /usr etc.

One of the beautiful things about linux is that, more often than not, there is more than
one way to do things.  And here is one way :)

Introduction
------------

Since the requirement is to be able to boot either disk, then neither disk being used for booting
purposes can have any hard dependency on the other disk. That means each disk 
must have its own *<esp>* and contain the same key partitions holding the operating system.

For convenience,  we partition each disk the same way. 
We choose the following standard set of partitions :

.. table:: Disk Partitions
   :align: center

   ========= ======== ============ ==================================
   Partition Required Approx Size  Comment
   ========= ======== ============ ==================================
   <esp>     yes      2 GB         FAT32, larger if no /boot
   boot      no       4 GB         linux filesystem 
   root      yes      100 GB
   swap      no       16 GB        
   home      yes      128 - 256 GB Optional if on different disk
   data      no       rest         Cache, RAID or mounted filesystem
   ========= ======== ============ ==================================

The important partitons for the purpose at hand are the first 3 (esp, root and boot).
Some schemes do not have a separate boot partition, but instead use a 
larger <esp> partition mounted on */boot* - that works for this pupose
as well, with obvious adjustments. The most important thing is each disk has its own <esp> 
partition.

Preparing the Alternate Disk
============================

Clearly it doesn't matter whether the disks are SSD or spinners.
For simplicity we'll assume the current booting disk is /dev/sda and the alternate
is /dev/sdb.  Adjust device names as needed.

Partitioning the disk
---------------------

Use gdisk to make the 6 partitions as illustrated in Table-1_. While there are
obviously different choices one can make, each disk must have at a minimum 
an *<esp>* (EFI) and *root* partitions. Since we want to have the system be the same
regardless which disk is used to boot the system, we want both disks to be similarly 
partitioned - at least for the key partitions (esp, boot, root).

.. _Table-1:

.. table:: Sample Disk Partition
   :align: center


   +-------------+------+------------+--------------+--------------+--------------+
   | Partition   | size | GPT Type   | Label        | Mount        | Comment      |
   +=============+======+============+==============+==============+==============+
   | 1           |   2G | EF00       | EFI          | /efi         |              |
   +-------------+------+------------+--------------+--------------+--------------+
   | 2           |   4G | EA00       | boot         | /boot        | XBOOTLDR     |
   +-------------+------+------------+--------------+--------------+--------------+
   | 3           | 100G | 8300       | root         | /            |              |
   +-------------+------+------------+--------------+--------------+--------------+
   | 4           |  16G | 8200       | swap         |              |              |
   +-------------+------+------------+--------------+--------------+--------------+
   | 5           | 128G | 8302       | home         | /home        |              |
   +-------------+------+------------+--------------+--------------+--------------+
   | 6           | rest | 8300       | data         | /data        | if mounted   |
   +-------------+------+------------+--------------+--------------+--------------+


Labels might also have a suffix indicating the disk number. For example, *root0* and *root1*
Each mounts the other disk's partitions under */mnt/root1/xxx* to allow the non-booted 
disk to be kept in sync with the currently booted disk.

Partition 6 may or may not be mounted - for example it could be part of a raid array.

Put Filesystem on alternate disk
---------------------------------

The starting point is a working system and the presence of the second disk to be used
for the alternate root.  For completeness, we'll quickly go over making appropriate
filesystems. Again, the critical one is the <esp> which must be FAT32. 

Now lets make filesystems on the alternate disk's partitions. We use ext4 for the
linux partitions as its robust and well supported.

.. code:: bash

   mkfs.vfat -n EFI2 /dev/sdb1
   mkfs.ext4 -L boot2 /dev/sdb2
   mkfs.ext4 -L root2 /dev/sdb3
   mkfs.ext4 -L home2 /dev/sdb5
   mkfs.ext4 -L data2 /dev/sdb6
   mkswap -L swap2 /dev/sdb4

Copy current system to alternate
================================

We'll make a copy of everything on the currently booted disk onto the alternate disk.
Each disk has some things which are unique to the disk. The root drive
is, by definition, unique and it's UUID is used for both booting and in 
its *fstab* to ensure things are mounted appropriately.

First we make a copy of everything relevant on the current disk - then we'll make 
the appropriate changes on the alternate to accomodate the different disk UUIDs.

While in spirit we are copying everything, we actually need to be a little more surgical.
For example, we dont want to copy /dev, /sys, /proc or even tmpfs directores such as /tmp. 
Instead we copy only the things we actually need.

For example we might populate the alternate using:

.. code:: bash

    mkdir -p /mnt/root1
    mount /dev/sdb3 /mnt/root1 
    cd /mnt/root1
    mkdir -p boot data dev efi etc home mnt opt proc root run srv sys usr var tmp
    # if you have any NFS mount points add as needed

    alt="/mnt/root1"
    opt="-avxHAX --exclude=/lost+found/ --delete --info=progress"
    rsync $opt /efi/EFI $alt/efi/
    rsync $opt /boot/* $alt/boot/
    rsync $opt /bin /lib /lib64 /usr $alt/
    rsync $opt /root $alt/
    rsync $opt /var $alt/
    rsync $opt /etc $alt/
    rsync $opt /data/* $alt/data/
    rsync $opt /srv $alt/
    rsync $opt /home $alt/

Modifications for different UUIDs
----------------------------------

Now that the alternate disk has its own copy of the system, we need to make the 
appropriate modifications so booting and mounting reference the correct disk. 
If we didn't change it, they would all be referring to the first disk. 

First lets fixup mounts.

Updating fstab 
--------------

First lets edit the alternate disk's fstab - we'll also add a few lines to mount  
first (currently booted) disk under /mnt/root1.

Identify the UUIDs of the alternate disk using blkid or lsblk::


   # lsblk -f /dev/sdb
   NAME   FSTYPE FSVER LABEL UUID                                 FSAVAIL FSUSE% MOUNTPOINTS
   sdb
   ├─sdb1 vfat   FAT32 EFI   74B3-8D8F                                 2G     0% /efi
   ├─sdb2 ext4   1.0   boot  0436e342-856a-495e-bd07-5f0dab1525fe    3.3G     9% /boot
   ├─sdb3 ext4   1.0   root  385c796c-a046-4bcb-b0e6-bec6dd543faa   68.9G    24% /
   ├─ ...


Our focus is on <esp>, boot and root. If you're using /home or /data then record those as well.

Now edit **/mnt/root1/fstab** (NOT /etc/fstab!) and duplicate the existing 3 lines 
for /, /efi and /boot, Next change the UUID to be the ones from the alternate disk obtained above.

In same fstab, change the mount points for the other disk so they now all get mounted under */mnt/root1*:

  - change */* to */mnt/root1* 
  - change */efi* to */mnt/root1/efi* 
  - change */boot* to */mnt/root1/boot* 

Of course, do same for any other mounted partitions (e.g. /home).

Lastly, edit the current disk's **/etc/fstab** and add mounts for the new alternate disk - 
now the alternate disk gets mounted under /mnt/root1. 

One that's done, each fstab has mounts for the *other* disk on /mnt/root1, /mnt/root1/efi, /mnt/root1/boot etc.


Updating systemd-boot loader entries
-------------------------------------

The boot loader entries that are used by sd-boot each 
reference the root disk. We must now update those on the alternate disk to point to their own (alternate) disk.  

Edit each entry in **/mnt/root1/boot/loader/entries/\***
and change the kernel option line::

    options root="UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" rw

to have the correct UUID found above - in our case this would be::

    options root="UUID=385c796c-a046-4bcb-b0e6-bec6dd543faa" rw

Once they're all done we're almost ready - in the next section we'll install a boot loader.

systemd-boot install
--------------------

All that's needed now is to install boot loader into the alternate <esp>. sd-boot makes this
straightforward to do::

   name='--efi-boot-option-description="02 Linux Boot Manager"'
   bootctl --esp-path /mnt/root1/efi --boot-path /mnt/root1/boot $name install

We specify a descriptive name, so that any system boot menu will show a different name 
than the default used for the first disk. The name of either can be easily changed at any time.

This will also put the alternate disk first in the boot order - you can leave it or change it back to
original disk - we'll discuss more below.  First lets check to make sure things look good. 

Check the current booted disk::

    bootctl status

This should look same as always. Now let check the alternate disk::

   bootctl --esp-path /mnt/root1/efi --boot-path /mnt/root1/boot status

This should look good. Please note sd-boot may issue or issues a warning
which can safely be ignored. 

bootctl compares the esp UUID with the UUID of the esp that was used to boot the current system.  
It warns if they differ.  
Well they should differ by design  - we want 2 <esp> each with its own UUID.
So this is a *good* thing. The warning will happen for whichever disk is NOT currently booted.

Its also a good idea to check the boot order saved in the efi variables::

   efibootmgr

You should now see both Linux entries listed.

Testing and Tidying Up
======================

At this point we are ready to test. There are a few non-essential convenience things 
that may be desirable.  

We changed the boot desciption - we may also want to change the boot desctiption of the 
original disk's <esp> as well. If we have not rebooted, then the original disk <esp> is mounted on /efi::

   bootctl --esp-path /efi --boot-path /boot \
           --efi-boot-option-description='01 Linux Alt' install

This will also make this disk the first in the boot order.  Boot order can also be changed
using *efibootmgr*. For this case we don't need to specify the esp or boot paths as they
are the defeaults. Doing it this way makes it explicitly clear.

It may be useful to change the title of each loader entry - e.g. ::
  
    [/mnt/root1]/boot/loader/entries/xxx.conf

Perhaps prefix the title with 01 or 02 depending which disk it is for. 

Be careful with the loader entry file names.  If name is changed then the 
/efi/loader/loader.conf, which references the filename in 
the *default* line, will need it's filename changed to match.
    

Keeping Disks In Sync
======================

Finally, we need to keep the disks in sync.  The simplest way to do this is run a little script
which rsync's from current booted linux to the alternate mounted under /mnt/root1 and
of course make sure NOT to replace fstab or the sd-boot loader entries.  Just run script out of cron.
or manually when so inclined. You can also add a pacman hook (on arch anyway) to trigger an update of
the alternate <esp> whenever systemd is updated. Or simply run it in the sync script.
    
Make sure the sync script is available on both disks!

This is a sample sync script:

.. code:: bash

    #!/bin/bash
    #
    # Copy files from currently booted system
    # into alternate mounted on /mnt/root1
    #  
    # NB
    # - do NOT copy fsteb or any loader entries.
    #   - Surefire way to break boot.
    # - Skip package cache 
    # 
    # To Add:
    #   ** check /mnt/root1 is properly mounted before rsync
    #
    alt="/mnt/root1"

    opt="-axHAX --info=stats --exclude=/lost+found/ --delete"
    echo "Syn alternate root:"

    echo "  /efi/EFI"
      rsync $opt /efi/EFI $alt/efi/
    echo "  /boot"
      rsync $opt --exclude=/boot/loader/ /boot $alt/
    echo "  /bin /lib /lib64 /usr"
      rsync $opt /bin /lib /lib64 /usr $alt/
    echo "  /root"
      rsync $opt /root $alt/
    echo "  /var"
      rsync $opt --exclude=/var/cache/pacman/pkg/ /var $alt/
    echo "  /etc"
      rsync $opt --exclude=/etc/fstab /etc $alt/
    echo "  /data"
      rsync $opt /data $alt/
    echo "  /srv"
      rsync $opt /srv $alt/


One simple approach to keeping it in sync is just to run this from cron - twice a day or perhaps more often.
This is an example */etc/cron.d/syn-alternate* if the sync script is in */mnt* and */mnt/root1/mnt*::

    # sync alternate root
    05 2,14 * * * root /mnt/sync-root


Epilogue
---------

** Caution **

Unlike raid, we are not guaranteed perfect synchronization - more dynamic 
data need to be kept somewhere safe - like on RAID. This includes things in */var*
such as mail or databases. 

For example, my mail server bind mounts the mail spool from a RAID-6 array. Another place to keep 
an eye on is /var/lib - e.g. secondary DNS may keep things here. There well may be
other parts of /var, or perhaps all of it, that might be good candidates to be held on RAID.
Its also a good idea to give some thought to /etc as well.  

There is some discussion around dual root and some of the challenges using RAID1 
as an alterntive on the arch general mail list:

    https://lists.archlinux.org/archives/list/arch-general@lists.archlinux.org/thread/KAMOXQTWQCPCC5KNFF6IOUSFPMNMLIIW/

This brings me to a couple of todo items:

Todo #1: Sync Tool Using Inotify
    Build or use existing inotify tools to monitor an appropriate set of dirs to sync to the alternate. 

Todo #2: Use the same basic mechanism to do fast installs.
    Build a tool to do fresh installs from a template root drive.

One can imagine doing pretty much same thing but instead do a fresh install. Of course care 
needs to be taken to avoid any services that are unique to the template machine. The way
I might apprach this is take a workstation install (no services) and use same sync 
script to create a template to install from. 
May need a little tweaking but then the template could be rsync'ed over the
local network (or from a USB drive) it should be straightforward to get things installed
quickly and directly.  Need some scripting work and a good template machine to get the ball rolling.

License
---------

 - SPDX-License-Identifier: MIT
 - Copyright (c) 2023 Gene C 





