.. SPDX-License-Identifier: MIT


Dual Root Capable Linux System
==============================

AKA hot spare alternate root disk
---------------------------------

Goal
----
The goal is a system which is resilient to a failure of the root drive.
In the event of a root disk failure, an alternate root disk can be quickly deployed.
We expect that the UEFI bios will boot the alternate disk if the first one is 
unavailable - but one can always use the bios boot menu, the one that lets user choose which drive to
boot, where both root disks should be offered. 

There are different ways to achieve this but they all share one key aspect which
is having two drives with each drive having its own *<esp>*.

We outline two approaches here, the first, and preferable, choice works well when doing
a fresh install and the second approach works when adding to an existing system
where the goal is to keep machine running and not start over with new install.

There are other possibilities but some may be risky and hacky in nature. We advocate
systems that are robust, clean and transparent.

The methods outlined here will have some partitions which need to be kept synchronized,
at a minimum this includes the <esp>. Other partitions will either be protected by
RAID (RAID-1 or higher) or will be kept synchronized. Synchronizing is best limited
to those areas which are stable rather than things that constantly changing, such as mail 
or databases. These *dynamic* areas should, if at all possible, be protected by RAID.

Since the requirement is to be able to boot either disk, then neither disk used for booting
purposes can have any hard dependency on the other disk. That means each disk 
must have its own *<esp>* and provide the same key partitions holding the 
operating system.

The 2 approaches outlined here both use:

 - 2 disks
 - each disk has an <esp> partition kept in sync
 - there are no constraints on each disk other than they each have sufficient capacity.

First Approach:  [1]_
 - Best Approach [2]_
 - Best suited for fresh installs
 - sync <esp>
 - keep kernel and initrd on <esp>
 - Everything else is mirrored using btrfs raid1
 - Only <esp> to sync and rest being mirrored
 - Downtime long if upgrading existing system
 - Starting point is fresh install using 2 disks. 
 - If existing root drive is the 3rd drive, downtime here is also kept to minimum.
 - If using SSD, then its best if both drives are SSDs for raid
 - Which ever disk's <esp> is used to boot, share same loader configs


For those who prefer to keep their kernels on a linux filesystem,
it is easy enough to use a separate /boot partition of type XBOODLDR.
These would need to be synced in addition to the <esp>. 

I have not tested this, but it may be possible to bind the 2 boot partitions with
a btrfs raid1. In the usual case, the loader finds the XBOOTLDR partition
on the same disk as the esp. With raid spanning the 2 disks, each of
type XBOOTLDR it may or may not work. 

.. [1] As discussed on Arch Geneal Mail List [3]_ with thanks to Óscar Amor for the basic idea.
.. [2] See Lennart Poettering's Blog "Linux Boot Partitions" [4]_
.. [3] https://lists.archlinux.org/archives/list/arch-general@lists.archlinux.org/thread/KAMOXQTWQCPCC5KNFF6IOUSFPMNMLIIW/
.. [4] https://0pointer.net/blog/ 

Second Approach:
 - best suited with minimal change upgrade  existsing system
 - syncing <esp, boot, root, usr and possibly var
 - dynamic areas (e.g. var) should preferably be on a RAID array.
   Especially if there are things like mail or databses running.
   What I do is keep these on separate RAID-6 and bind mount them into var
 - All thats needed is second with adequate disk space
 - Downtime is only the few minutes to install 2nd disk.  Configuration while up and running normally.
 - Starting point is a working linux computer using systemd-boot. 
 - If using SSD, then best if the primary boot drive uses SSD
 - Each boot now has its own /boot, and thus different boot loader config UUIDs


We use Archlinux but the distro shouldn't play any significant role in dual root setup. 
We find the Arch rolling release distro convenient and robust.

One of the beautiful things about linux is that, more often than not, there is more than
one way to do things.  And here is one way :)

**Todo** ::

    Create Inotify based sync tool to improve on the simple sync script below.

First Approach
================

Each of the two disks to be used needs its own <esp> and root partitions.
The <esp> will eventually be mounted as /boot in linux.

Make the <esp> partitions each the same size - 1 - 2 GB provides plenty of room for multiple kernels.
While btrfs raid mirror doesn't require equal sized partitions, if the disks are different sizes, 
then there will be unused space. Ignore it or make the 2 roots the same size, and create 
an extra partition on the larger one. That extra partition will not be part of the raid1 obviously.

Can also be a swap partition if desired, but it plays no direct role here.

If converting an existing setup, then backup everything either to another disk, external 
or internal or over the network to another computer. Otherwise we assume starting with
fresh install.

This methos has a tricky part to sort out, which is that we have one root but 2 esp partitions.
After the machine boots we will mount both <esp> partitions, 
and we need to know which one was used to boot so that we can sync it to the other one.
We'll explain how to do that in a robust way a little later.

Partition sizing: 
----------------

For example, if we use 2 GB <esp> partition and the root partition be rest of disk.
In this example the <esp> as on sda1 / sdb1, swap partitions are sda2 / sdb2  
and the root partitions are on sda3 / sdb3.

We are now ready to put filesystems on the disks. First format the <esp> partitions::

    mkfs.vfat -n EFI0 /dev/sda1
    mkfs.vfat -n EFI1 /dev/sdb1

Each gets its own swap in this example::

    mkswap -L swap0 /dev/sda2
    mkswap -L swap1 /dev/sdb2

And then the root filesystems::

    mkfs.btrfs -L root -m raid1 -d raid1 /dev/sda2 /dev/sdb2

In this example the first disk is larger than the second, so we use the 
extra space to create a *data* partition.

Lets look at what we have and identify the UUIDs we'll need as well::

    # lsblk f
    lsblk -f
    NAME   FSTYPE FSVER LABEL UUID                                 FSAVAIL FSUSE% MOUNTPOINTS
    sda
    ├─sda1 vfat   FAT32 EFI0  6B7E-A837
    ├─sda2 swap   1     swap0 285c7969-f137-4b3e-b89e-fabe81e44eb1
    ├─sda3 btrfs        root  a8426465-b755-429d-9604-9c77c2838fda
    └─sda4 ext4   1.0   data0 315025e3-26a7-4d3e-a3af-cfb8f7cea339
    sdb
    ├─sdb1 vfat   FAT32 EFI1  6C48-1623
    ├─sdb2 swap   1     swap1 3651f9e6-85a1-464d-ac70-74d3d085f577
    └─sdb3 btrfs        root  a8426465-b755-429d-9604-9c77c2838fda

To continue we'll use temporary mounts::

    mkdir -p /mnt/root
    mount UUID=a8426465-b755-429d-9604-9c77c2838fda /mnt/root

    cd /mnt/root
    mkdir -p boot data dev efi etc home mnt opt proc root run srv sys usr var tmp

    mkdir /mnt/root/efi0 /mnt/root/efi1
    mount /dev/sda1 /mnt/root/efi0
    mount /dev/sdb1 /mnt/root/efi1
    mount --bind /mnt/root/efi0 /mnt/root/boot 

At this point either use arch-chroot and install as usual or rsync from an appropriate backup. 
With this set up the efi is to be mounted bind /boot. We use a bind mount of efi0 onto /boot.
We will always mount both <esp> partitions under /efi0 and /efi1. We will also be bind 
mounting one of them onto /boot for convenience.

If you're pulling from backup then regenerate all initrds to be sure they are consistent
with the current set up. Don't skip this step :)

Make sure that the systemd-loader entries, located in /mnt/root/boot/efi/loader/entries
have the correct option root line. In our example the load entry for arch kernel
would be::

    title   Linux Arch
    linux   /vmlinuz-linux
    initrd  /initramfs-linux.img
    initrd  /intel-ucode.img 
    options root="UUID=a8426465-b755-429d-9604-9c77c2838fda" rootfstype=btrfs rw audit=0

As you see the UUID is the btrfs one shown above.

We now use systemd bootctl to install both <esp>s::

    bootctl --efi-boot-option-description='Linux esp 1' --esp-path /mnt/root/efi1 install
    bootctl --efi-boot-option-description='Linux esp 0' --esp-path /mnt/root/efi0 install

The second line could just as well be::

    bootctl --esp-path /mnt/root/boot install

Doing it in this order makes the boot order efi0 then efi1. 

Now run bootctl to check everything looks good and check boot order::
    
    bootctl --esp-path /mnt/root/efi0 status
    bootctl --esp-path /mnt/root/efi1 status
    efibootmgr

Now we still need to adjust the new /mnt/root/etc/fstab. In the fstab we will
mount both efi partitions. Later we will create a mechanism to bind mount
whichever <esp> was used onto /boot. Before we do this lets test to make sure
it boots okay.

Adjust the /mnt/root/fstab to mount each <esp> under /efi0 andf /efi1
And mount the btrfs root onto /.  You can get the mounts to use by::

    cd /mnt/root
    genfstab -U .

In our case fstab looks like ::

    # /dev/sda3 UUID=a8426465-b755-429d-9604-9c77c2838fda LABEL=root
    UUID=a8426465-b755-429d-9604-9c77c2838fda / btrfs rw,relatime,ssd,discard=async,space_cache=v2,subvolid=5,subvol=/  0 0

    # /dev/sda1 UUID=6B7E-A837 LABEL=EFI0
    UUID=6B7E-A837 /efi0 vfat rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=iso8859-1,shortname=mixed,utf8,errors=remount-ro 0 0

    # /dev/sdb1 UUID=6C48-1623 LABEL=EFI1
    UUID=6C48-1623 /efi1 vfat  rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=iso8859-1,shortname=mixed,utf8,errors=remount-ro    0 0

    
Delete the mount of /boot. We will come
back to this later after we have a mechanism to decide which of the 2 <esp> to
bind mount onto /boot.

Before we go ahead and boot let's regenerate the initrds - this will of course only work
provided the active efi was bind mounted onto /boot as per above.

All being well you should be able to boot the system. Next we will deal mounting */boot* and
syncing the efi partitions - the tricky bit! You don't need to reboot at this point,
you can continue to the next section where we provide an automatic mechanism to
have the whichever <esp> was booted to be bind mounted on /boot.


Mounting /boot 
--------------

This is a little tricky. I was hoping bootctl -p would be a reliable way to detect which
<esp> was used for current boot, but I didn't find a reliable way. Instead I wrote a little script
to identfify which <esp> was used and mount then bind mount it onto /boot. My script is in 
python, mainly as I found doing it in bash unpleasant. Perhaps someone better with scripting
might make a bash version.

So whats needed is to install the script in /usr/bin/bind-mount-efi. 
Copy the systemd service file to /etc/systemd/system/bind-mount-efi.service. Then enable the service 
with the usual incantation::

    systemctl enable bind-mount-efi

Next add a mount option to both the efi0 and efi1 mount lines in /etc/fstab 
(or /mnt/root/etc/fstab if you have not booted machine yet). In my example, the efi0 line 
gets additional option: x-systemd.before=bind-mount-efi.service. Same of efi1 naturally::

    UUID=6B7E-A837 /efi0 vfat rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=iso8859-1,shortname=mixed,utf8,errors=remount-ro,x-systemd.before=bind-mount-efi.service 0 0


What this does is ientify which if the 2 <esp> was booted and then bind mounts that one onto /boot

Now was have /boot being the 'actively booted' efi. We have overcome the trickiest part of all this.

Now  is a good time to reboot - all should work and you should have /boot from the actively booted
<esp>.


Syncing ESPs
-------------

Now that we know the active <esp> we are able to sync the other <esp> from that one.

This section and the code to identify active <esp> and bind mount it will be made available soon.




Second Approach
===============


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
---------------------

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
========

There is some discussion around dual root and some of the challenges using mdadm RAID1 
on the arch general mail list [3]_.

This brings me to a couple of todo items:

**Todo** #1: Sync Tool Using Inotify
    Build or use existing inotify tools to monitor an appropriate set of dirs to sync to the alternate. 

**Todo** #2: Use same basic mechanism as Second Approach to do fast installs.
    Build a tool to do fresh installs from a template root drive.

For an install, one can imagine doing pretty much same thing as the second approach,
but instead do a fresh install from a template. 
Of course care needs to be taken to avoid any services that are unique to the template machine. 
One way to apprach this might be to take a workstation install 
(with no services like mail, databases, etc) and use sync script to create a template to install from. 

May need a little tweaking but then the template could be rsync'ed over the
local network (or from a USB drive). This should make it reasonably straightforward and 
fast to get things installed.  Needs some scripting work and a good template machine to get the ball rolling.

License
========

 - SPDX-License-Identifier: MIT
 - Copyright (c) 2023 Gene C 





