title: Getting the Huawei E352s-5 to work with Linux
date: 2013-04-27 16:18
tags: linux
category: linux
slug: huawei_e352s5
author: Philipp Wagner

# getting the Huawei E352s-5 to work with linux #

Yes, I am alive and well! This is just a quick note on how to get a Huawei E352s-5 working under Linux. Today I've upgraded my contract to a new mobile data plan and I got a Huawei stick with it, which seems to be the latest model [T-Mobile](www.t-mobile.de) sells you in Germany (and now you know I am at the monopolist). If you buy hardware without researching the internet thoroughly, you'll almost always need some effort to get it working with Linux, especially if you aren't on the latest distribution.  I am running an Ubuntu 10.10 installation and I've been quite happy with it ever since. As expected, the modem isn't recognized by Ubuntu 10.10. It's not a big deal this time, since Huawei modems are pretty common.

## switching into modem mode ##

If you have inserted your SIM card, plugged in the Huawei E352s-5 stick and your distribution recognized it... you can stop reading here. But if you are on an old distribution like I am, you'll probably need to use [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) to get it working. First of all, let's see what ``dmesg`` says after inserting the stick:

<pre>
philipp@mango:~$ dmesg
...
[   48.220072] usb 2-5: new high speed USB device using ehci_hcd and address 4
[   48.362048] scsi5 : usb-storage 2-5:1.4
[   48.367660] scsi6 : usb-storage 2-5:1.5
[   49.365716] scsi 5:0:0:0: CD-ROM            HUAWEI   Mass Storage     2.31 PQ: 0 ANSI: 2
[   49.368325] sr1: scsi-1 drive
[   49.368854] sr 5:0:0:0: Attached scsi CD-ROM sr1
[   49.369011] sr 5:0:0:0: Attached scsi generic sg2 type 5
[   49.372964] scsi 6:0:0:0: Direct-Access     HUAWEI   SD Storage       2.31 PQ: 0 ANSI: 2
[   49.374988] sd 6:0:0:0: Attached scsi generic sg3 type 0
[   49.380995] sd 6:0:0:0: [sdb] Attached SCSI removable disk
[   49.511962] ISO 9660 Extensions: Microsoft Joliet Level 1
[   49.542715] ISOFS: changing to secondary root
</pre>

So the device seems to register as an USB Mass Storage device, running ``lsusb`` shows us the the Vendor and Product ID:

<pre>
philipp@mango:~$ lsusb
...
Bus 002 Device 008: ID 12d1:14fe Huawei Technologies Co., Ltd. 
</pre>

Fine, let's see how to switch the device into its Modem mode! There is a nice open source project called [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch), which does the job. The [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) coming with my Ubuntu 10.10 is rather outdated, so I'll build it from source. You'll need ``libusb-dev`` to build it, so if you haven't installed it yet you can simply install it via ``apt-get`` (or your distributions package manager). [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) seems to play fine with most of the ``libusb-dev`` versions:

```sh
sudo apt-get install libusb-dev
```

Next we'll download, unpack and install the most recent versions of [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) and its [usb_modeswitch-data](http://www.draisberghof.de/usb_modeswitch/). Installing [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) is easy, I guess you are familiar with the commands:

```sh
# Download sources:
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-1.2.5.tar.bz2
tar xjf usb-modeswitch-1.2.5.tar.bz2
cd usb-modeswitch-1.2.5
sudo make install
```

Do the same for the [usb_modeswitch-data](http://www.draisberghof.de/usb_modeswitch/), which contains a lot of udev scripts, that *might* cover your hardware already:

```sh 
wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-data-20121109.tar.bz2
tar xjf usb-modeswitch-data-20121109.tar.bz2
cd usb-modeswitch-data-20121109
sudo make install
```

The new [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) overrides the old version, so no need to take care about the installation path! With [usb_modeswitch](http://www.draisberghof.de/usb_modeswitch/) it's easy to switch the Huawei E352-s into the Modem mode. A quick research is going to reveal you the switching command. I guess it's the sniffed packet Windows sends to the device in order to switch modes, I really don't feel the need to sniff it all by myself (you have to run the commands as root):

```sh
usb_modeswitch -v 12d1 -p 14fe -M '55534243123456780000000000000011062000000100000000000000000000' 
```

Now running ``lsusb`` reveals a new Product ID:

<pre>
philipp@mango:~$ lsusb
...
Bus 002 Device 022: ID 12d1:1506 Huawei Technologies Co., Ltd
</pre>

Using the ``option`` module should register us the modem:

```sh
modprobe option
echo "12d1 1506" > /sys/bus/usb-serial/drivers/option1/new_id
```

Running ``dmesg`` (or looking at ``/var/log/messages`` if you prefer) reveals:

<pre>
philipp@mango:~$ dmesg
...
[ 1471.905063] usb 2-5: new high speed USB device using ehci_hcd and address 12
[ 1472.039036] option 2-5:1.0: GSM modem (1-port) converter detected
[ 1472.039214] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB0
[ 1472.039374] option 2-5:1.1: GSM modem (1-port) converter detected
[ 1472.039522] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB1
[ 1472.039647] option 2-5:1.2: GSM modem (1-port) converter detected
[ 1472.039751] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB2
[ 1472.039893] option 2-5:1.3: GSM modem (1-port) converter detected
[ 1472.039997] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB3
[ 1472.040173] option 2-5:1.4: GSM modem (1-port) converter detected
[ 1472.040268] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB4
[ 1472.040404] option 2-5:1.5: GSM modem (1-port) converter detected
[ 1472.040496] usb 2-5: GSM modem (1-port) converter now attached to ttyUSB5
</pre>

The modem should be usable by now and your network-manager should ask you for the PIN to unlock the device. Congratulations!

## udev rules ##

We don't want to impress people by remembering these cryptic lines, so you could write two ``udev`` rules to execute these commands whenever the device is added to the USB subsystem. Store it to ``/etc/udev/rules.d/70-huawei_e352.rules`` for example.

**Filename** ``/etc/udev/rules.d/70-huawei_e352.rules``:

<pre>
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="12d1", ATTRS{idProduct}=="14fe", RUN+="/usr/sbin/usb_modeswitch -v 12d1 -p 14fe -M '55534243123456780000000000000011062000000100000000000000000000'"
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="12d1", ATTRS{idProduct}=="14fe", RUN+="/bin/bash -c 'modprobe option && echo 12d1 1506 > /sys/bus/usb-serial/drivers/option1/new_id'"
</pre>

And reload the rules:

<pre>
udevadm control --reload-rules
</pre>

And that's it basically! Your stick should now be put into Modem mode automatically, whenever you plug it in.

## final note ##

I have noticed, that my Ubuntu 10.10 ``modem-manager`` sometimes has problems to recognize the device after reattaching it. This happens especially after restoring my system from hibernation. Restarting the ``network-manager`` service doesn't help here either. I know it doesn't sound great, but killing the ``modem-manager`` process works great for me:

<pre>
philipp@mango:~$ ps ax | grep modem-manager
 3914 ?        S      0:00 /usr/sbin/modem-manager
 philipp@mango:~$ sudo kill 3914
</pre>

It is automatically restarted by the ``network-manager`` and the magic happens. If I have some time, I might take a look at it. But I guess it has been fixed in recent versions or doesn't apply to the recent Unity based Ubuntu distributions at all.

## useful links ##

* [http://www.draisberghof.de/usb_modeswitch/](http://www.draisberghof.de/usb_modeswitch/)
