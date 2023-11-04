.. SPDX-License-Identifier: MIT


MDADM RAID + CACHE
==================

Setting up RAID-6
-----------------

We will use *mdadm* for the RAID setup. Once that's done we will make a 
logical volume with one volume group and the raid array added as physical volume in the 
volume group. 

We use ext4 filestem on top of that.  The last step is to
add lvmcache using the unused partition of an nvme SSD.

Thats the basic idea and now we'll provide a quicksummary of the steps to do that.
A huge thank you to Steve K for bringing this to my attention.

To illustrate lets assume that the RAID array is built from partition 6 of 
6 disks. We create and assemble the array as follows:

.. code:: bash

    mdadm --create --verbose --level=6 --chunk=512K --raid-devices=6 --homehost any \
        /dev/md/data  /dev/sda6 /dev/sdb6 /dev/sdc6 /dev/sdd6 /dev/sde6 /dev/sdf6
    cat /proc/mdstat
    mdadm --detail /dev/md127
    mdadm --detail --scan >> /etc/mdadm.conf
    mdadm --assemble --scan

Adjust the devices to match whatever devices and partitions are used if different than the example.
Next we will make the new raid device a physical volume and add it into a 
volume group called *vg_data*: 

.. code:: bash

   pvcreate /dev/md/data
   pvdisplay

   vgcreate vg_data /dev/md/data
   vgdisplay


and now make volume group part of a logical volume called *lv_data*:

.. code:: bash

   lvcreate -l 100%FREE vg_data -n lv_data
   lvdisplay

Lets add a filesystem onto the logical volume:

.. code:: bash

   mkfs.ext4 -v -L "data" -b 4096 -E stride=128,stripe-width=512 /dev/vg_data/lv_data

For good measure lets quickly check on the array itself:

.. code:: bash

   cat /etc/mdadm.conf
   mdadm --examine --scan


Next step is to extend the volume group with cache, for which we use */dev/nvme0n1p6* 
in our case:

.. code:: bash

   vgextend vg_data /dev/nvme0n1p6
   lvcreate --type cache --cachemode writethrough -l 100%FREE -n data_cache \
      vg_data/lv_data /dev/nvme0n1p6

Edit /etc/fstab and add a mount for new cached RAID-6 storage - we'll mount it on 
*/mnt/lv_data* ::

    mkdir /mnt/lv_data
    # Add this to fstab:
    /dev/vg_data/lv_data /mnt/lv_data ext4    rw,relatime 0

    # tell systemd fstab has changed
    systemctl daemon-reload
    mount /mnt/lv_data


Add an email address to receive the mdadm monitor service reports; edit
*/etc/mdadm.conf* and add root email::

   MAILADDR root@xxx.com

Enable and start the raid monitor:

.. code:: bash

   systemctl enable mdmonitor.service
   systemctl start mdmonitor.service


That's it - we now have fast SSD cache in front of the RAID array.

License
--------

 - SPDX-License-Identifier: MIT
 - Copyright (c) 2023 Gene C

