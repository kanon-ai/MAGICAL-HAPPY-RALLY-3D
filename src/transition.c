#include "hardware.h"
/* Two unused atlas regions hold the incoming panorama. No visible tile is
 * overwritten until the sideways reveal has completely finished. */
static void sky_part(u16 sx,u16 dx,u16 y,u16 width,u8 incoming){
 u16 first=256-sx;
 if(first>width)first=width;
 if(incoming){
  gfx_blit(sx,590,dx,y,first,60,0);gfx_blit(sx,720,dx,y+60,first,18,0);
  if(width>first){gfx_blit(0,590,dx+first,y,width-first,60,0);gfx_blit(0,720,dx+first,y+60,width-first,18,0);}
 }else{
  gfx_blit(sx,512,dx,y,first,78,0);
  if(width>first)gfx_blit(0,512,dx+first,y,width-first,78,0);
 }
}
void draw_scene_sky(u16 pan,u16 y,u16 mix){
 if(mix<256)sky_part((pan+mix)&255,0,y,256-mix,0);
 if(mix)sky_part(pan,256-mix,y,mix,1);
}

extern volatile u8 route_piece,tunnel_cover;
extern volatile u16 distance;
u16 scene_pan;
extern u8 beach_factor;
void update_scene_transition(void){
 tunnel_cover=0;scene_pan=0;beach_factor=0;
 if(route_piece==7&&distance>=8192)beach_factor=distance<12288?(distance-8192)>>5:128;
 if(route_piece==8&&distance<4096)beach_factor=128-(distance>>5);
 if(route_piece==7&&distance>=14336)scene_pan=(distance-14336)>>4;
 if(route_piece==8)scene_pan=distance<2048?128+(distance>>4):256;
 if(route_piece>8)scene_pan=256;
}

u8 beach_factor;
u16 beach_extra;

void translate_left_mesh(u8 *mesh){
 u8 j,*v=mesh;
 s16 *d=(s16*)(mesh+40);
 for(j=0;j<8;++j,v+=5) *((s16*)v)+=*d++;
}
