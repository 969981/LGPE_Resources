
void FUN_710026f930(undefined8 *param_1,long *param_2,long *param_3,int *param_4)

{
  undefined *puVar1;
  uint *puVar2;
  undefined8 *puVar3;
  int *piVar4;
  ulong uVar5;
  
  if ((*(ushort *)((long)param_4 - (long)*param_4) < 5) ||
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[2], uVar5 == 0)) {
    piVar4 = (int *)0x0;
  }
  else {
    puVar2 = (uint *)((long)param_4 + uVar5);
    piVar4 = (int *)((long)puVar2 + (ulong)*puVar2);
  }
  FUN_71002175e0(param_1,param_2,param_3,piVar4);
  puVar1 = PTR_DAT_71015fe9e0;
  param_1[0x91] = 0;
  param_1[0x90] = 0;
  param_1[0x8f] = 0;
  param_1[0x8e] = 0;
  param_1[9] = puVar1 + 0x138;
  param_1[10] = puVar1 + 0x170;
  *param_1 = puVar1 + 0x10;
  param_1[0x8d] = 0;
  param_1[0xa7] = 0;
  param_1[0xa6] = 0;
  param_1[0xa5] = 0;
  param_1[0xa4] = 0;
  param_1[0x97] = 0;
  param_1[0x96] = 0;
  param_1[0x95] = 0;
  param_1[0x94] = 0;
  puVar1 = PTR_DAT_71015fbbf8 + 0x10;
  param_1[0xb4] = puVar1;
  param_1[0x92] = puVar1;
  param_1[0xd6] = puVar1;
  param_1[0xf8] = puVar1;
  param_1[0x11a] = puVar1;
  puVar3 = param_1 + 0x31;
  if (param_1[0x33] != -0x340d631b7bddd9bb) {
    puVar3 = param_1 + 0x33;
  }
  param_1[0x93] = 0;
  param_1[0xc9] = 0;
  param_1[200] = 0;
  param_1[199] = 0;
  param_1[0xc6] = 0;
  param_1[0xb9] = 0;
  param_1[0xb8] = 0;
  param_1[0xb7] = 0;
  param_1[0xb6] = 0;
  param_1[0xb5] = 0;
  param_1[0xeb] = 0;
  param_1[0xea] = 0;
  param_1[0xe9] = 0;
  param_1[0xe8] = 0;
  param_1[0xdb] = 0;
  param_1[0xda] = 0;
  param_1[0xd9] = 0;
  param_1[0xd8] = 0;
  param_1[0xd7] = 0;
  param_1[0x10d] = 0;
  param_1[0x10c] = 0;
  param_1[0x10b] = 0;
  param_1[0x10a] = 0;
  param_1[0xfd] = 0;
  param_1[0xfc] = 0;
  param_1[0xfb] = 0;
  param_1[0xfa] = 0;
  param_1[0xf9] = 0;
  param_1[0x12f] = 0;
  param_1[0x12e] = 0;
  param_1[0x12d] = 0;
  param_1[300] = 0;
  param_1[0x11f] = 0;
  param_1[0x11e] = 0;
  param_1[0x11d] = 0;
  param_1[0x11c] = 0;
  param_1[0x11b] = 0;
  param_1[0x140] = 0;
  param_1[0x13f] = 0;
  param_1[0x13e] = 0;
  param_1[0x13d] = 0;
  param_1[0x13c] = 0;
  *(undefined2 *)((long)param_1 + 0xa74) = 0;
  param_1[0x33] = *puVar3;
  *(undefined4 *)(param_1 + 0x14e) = 0xffffffff;
  return;
}

