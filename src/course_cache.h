/* ASCII16 upper-half profiles: banks 64..191, 32 records per half-bank. */
#include <string.h>
u8 cache_stage,mesh_bank,mesh_record,rear_profile[32];
u16 mesh_phase=65535;
volatile u16 cache_loads,cache_crossings;
static void cache_init(void){
 cache_stage=255;cache_loads=cache_crossings=0;
 /* Main mapper page 0: mesh 0100..02DF, reciprocal 0400..23FF,
  * view code 2400..3BFF, models 3C00..3DD3. BGM uses a different segment. */
 *((volatile u8*)0x6000)=192;memcpy((void*)0x0400,(const void*)0x6000,8192);
 *((volatile u8*)0x6000)=195;memcpy((void*)0x3c00,(const void*)0x7800,468);
 /* Dedicated chase LOD; player uses its resident projected mesh. */
 memcpy((void*)0x3dd4,(const void*)0x79d4,468);
 *((volatile u8*)0x6000)=214;memcpy((void*)0x2400,(const void*)0x6000,6144);
}
static void cache_prepare(u8 stage){cache_stage=stage;++cache_loads;}
void apply_coast_appearance(u16 phase);
static void cache_read(u16 phase){
 *((volatile u8*)0x6000)=64+(u8)(phase>>5);
 memcpy(profile,(const void*)(0x6000+((phase&31)<<8)),256);
 if(mesh_phase==65535||phase<mesh_phase||phase-mesh_phase>16){mesh_bank=1+phase/17;mesh_record=phase%17;}
 else {mesh_record+=(u8)(phase-mesh_phase);if(mesh_record>=17){mesh_record-=17;++mesh_bank;}}
 *((volatile u8*)0x6000)=196+(u8)(phase>>8);
 memcpy(rear_profile,(const void*)(0x6000+((phase&255)<<5)),32);
 mesh_phase=phase;
 *((volatile u8*)0x6000)=mesh_bank;
 memcpy((void*)0x0100,(const void*)(0x4000+(u16)mesh_record*480),480);
 apply_coast_appearance(phase);
}
static void stage_visuals(u8 stage){
 stage;hardware_upload();
 upload_stage_stream(master_banks[0],master_addresses[0],128,768);
 upload_stage_stream(master_banks[1],master_addresses[1],128,896);
 gfx_set_palette(night_palette);visual_night=0;
}
