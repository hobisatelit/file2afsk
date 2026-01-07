# file2afsk
Create AFSK 1200 modulated WAV audio from a binary file to be transmitted via a handheld FM radio, and vice versa. Example: send and receive SSDV image over AFSK 1200 modulation from terestrial or VR satellites

### Dependencies:
Debian/Ubuntu Linux
```bash
sudo apt install python3 direwolf sox github pavucontrol
```
### Optional:
install ssdv. look at [this link for detailed howto](https://github.com/daniestevez/ssdv)

### Download the script:
```bash
cd ~
git clone https://github.com/hobisatelit/file2afsk.git && cd file2afsk
chmod 755 tx.py rx.py
```
### Configuration:
edit tx.py, change SRC_CALL = "ABC" with your actual callsigner 

### How to convert file into WAV  
Run Direwolf KISS server
```bash
cd ~/file2afsk
direwolf -c direwolf.conf
```
on another terminal run
```bash
cd ~/file2afsk
./tx.py image.bin
```
### How to convert WAV into file
make sure your direwolf kiss server is running. look above for instruction
run pavucontrol
```bash
pavucontrol
```
look at recording tab, you will see direwolf app there, and change capture to monitor mode

```bash
cd ~/file2afsk
./rx.py
```
play your recorded wav file or SDR, and the rx.py script will detect the file inside the sound. when finish, prest ctrl+c. the binary file will be saved as .bin file in same directory

### How to encode JPG file into SSDV bin
```bash
ssdv -e -q 1 image.jpg image.bin
```
### How to decode SSDV bin file into JPG
```bash
ssdv -d image.bin image.jpg
```
