# 215Z blueprint
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://buymeacoffee.com/mauritsmalkus)
This blueprint is based on the work of vandalon, khvej8 and others as found in https://community.home-assistant.io/t/zigbee2mqtt-enocean-ptm-215z-friends-of-hue-switch/429770/ but recognized multi clicks and support media_players

## Setup of the blueprint
The blueprint is build is such a way to make setting up a button as easy as possible. For a single 215Z only one automation is needed and the use is split per left/right pair. So button 1/2 control one device, and button 3/4 control another device. 
Devices can either be lights (or a group of lights, as defined in Z2M) or a media_players. 

For light, the top button turns on the light or increases the brightness when held, the lower button turns of the light or decreases brightness.

For media players, the top button denotes play, and holding increases volume, the lower button denotes pause and holding lowers volume.

When buttons are pressed multiple times a scene is called, which is based on the scene prefix. E.g. if the scene prefix is 'kitchen' and the top right button (button 3) is pressed 2 times, the following scene is activated: 'kitchen_3_2'.
