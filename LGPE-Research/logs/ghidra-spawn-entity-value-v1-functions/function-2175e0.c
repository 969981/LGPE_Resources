
void FUN_71002175e0(undefined8 *param_1,long *param_2,long *param_3,int *param_4)

{
  uint *puVar1;
  ushort uVar2;
  undefined *puVar3;
  int *piVar4;
  ulong uVar5;
  undefined8 uVar6;
  ushort *puVar7;
  undefined4 uVar8;
  undefined4 uVar9;
  undefined4 uVar10;
  float fVar11;
  undefined4 uVar12;
  undefined4 uVar13;
  float fVar14;
  uint uVar15;
  uint uVar16;
  float fVar17;
  
  if ((*(ushort *)((long)param_4 - (long)*param_4) < 5) ||
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[2], uVar5 == 0)) {
    piVar4 = (int *)0x0;
  }
  else {
    puVar1 = (uint *)((long)param_4 + uVar5);
    piVar4 = (int *)((long)puVar1 + (ulong)*puVar1);
  }
  FUN_7100216f90(param_1,param_2,param_3,piVar4);
  puVar3 = PTR_DAT_71015fe678;
  param_1[0x7b] = 0;
  *param_1 = puVar3 + 0x10;
  param_1[9] = puVar3 + 0x130;
  param_1[10] = puVar3 + 0x168;
  *(undefined1 *)(param_1 + 0x7c) = 1;
  uVar6 = 0;
  if ((6 < *(ushort *)((long)param_4 - (long)*param_4)) &&
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[3], uVar6 = 0, uVar5 != 0)) {
    uVar6 = *(undefined8 *)((long)param_4 + uVar5);
  }
  param_1[0x7d] = uVar6;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 9) {
    uVar6 = 0;
  }
  else {
    uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[4];
    uVar6 = 0;
    if (uVar5 != 0) {
      uVar6 = *(undefined8 *)((long)param_4 + uVar5);
    }
  }
  param_1[0x7e] = uVar6;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 0xb) {
    uVar6 = 0;
  }
  else {
    uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[5];
    uVar6 = 0;
    if (uVar5 != 0) {
      uVar6 = *(undefined8 *)((long)param_4 + uVar5);
    }
  }
  param_1[0x7f] = uVar6;
  if ((*(ushort *)((long)param_4 - (long)*param_4) < 0xd) ||
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[6], uVar5 == 0)) {
    uVar6 = 0;
  }
  else {
    uVar6 = *(undefined8 *)((long)param_4 + uVar5);
  }
  param_1[0x80] = uVar6;
  *(undefined4 *)((long)param_1 + 0x40c) = 0;
  *(undefined1 *)(param_1 + 0x82) = 0;
  uVar12 = 0;
  *(undefined4 *)((long)param_1 + 0x414) = 0x25;
  if ((0xe < *(ushort *)((long)param_4 - (long)*param_4)) &&
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[7], uVar12 = 0, uVar5 != 0)) {
    uVar12 = *(undefined4 *)((long)param_4 + uVar5);
  }
  *(undefined4 *)(param_1 + 0x83) = uVar12;
  puVar1 = (uint *)((long)param_4 + (ulong)*(ushort *)((long)param_4 + (0x10 - (long)*param_4)));
  piVar4 = (int *)((long)puVar1 + (ulong)*puVar1);
  puVar7 = (ushort *)((long)piVar4 - (long)*piVar4);
  uVar8 = 0;
  uVar12 = 0;
  uVar9 = 0;
  uVar15 = 0;
  uVar2 = *puVar7;
  if (4 < uVar2) {
    uVar12 = 0;
    uVar9 = 0;
    if ((ulong)puVar7[2] != 0) {
      uVar9 = *(undefined4 *)((long)piVar4 + (ulong)puVar7[2]);
    }
    if (uVar2 < 7) {
      uVar15 = 0;
    }
    else {
      uVar15 = 0;
      uVar12 = 0;
      if ((ulong)puVar7[3] != 0) {
        uVar12 = *(undefined4 *)((long)piVar4 + (ulong)puVar7[3]);
      }
      if ((8 < uVar2) && ((ulong)puVar7[4] != 0)) {
        uVar15 = *(uint *)((long)piVar4 + (ulong)puVar7[4]);
      }
    }
  }
  uVar10 = 0;
  uVar13 = 0;
  uVar16 = 0;
  param_1[0x85] = (ulong)uVar15;
  param_1[0x84] = CONCAT44(uVar12,uVar9);
  puVar1 = (uint *)((long)param_4 + (ulong)*(ushort *)((long)param_4 + (0x10 - (long)*param_4)));
  piVar4 = (int *)((long)puVar1 + (ulong)*puVar1);
  puVar7 = (ushort *)((long)piVar4 - (long)*piVar4);
  uVar2 = *puVar7;
  if (0x10 < uVar2) {
    uVar13 = 0;
    uVar10 = 0;
    if ((ulong)puVar7[8] != 0) {
      uVar10 = *(undefined4 *)((long)piVar4 + (ulong)puVar7[8]);
    }
    if (uVar2 < 0x13) {
      uVar16 = 0;
    }
    else {
      uVar16 = 0;
      uVar13 = 0;
      if ((ulong)puVar7[9] != 0) {
        uVar13 = *(undefined4 *)((long)piVar4 + (ulong)puVar7[9]);
      }
      if ((0x14 < uVar2) && ((ulong)puVar7[10] != 0)) {
        uVar16 = *(uint *)((long)piVar4 + (ulong)puVar7[10]);
      }
    }
  }
  fVar11 = 0.0;
  fVar14 = 0.0;
  fVar17 = 0.0;
  param_1[0x87] = (ulong)uVar16;
  param_1[0x86] = CONCAT44(uVar13,uVar10);
  puVar1 = (uint *)((long)param_4 + (ulong)*(ushort *)((long)param_4 + (0x10 - (long)*param_4)));
  piVar4 = (int *)((long)puVar1 + (ulong)*puVar1);
  puVar7 = (ushort *)((long)piVar4 - (long)*piVar4);
  uVar2 = *puVar7;
  if (10 < uVar2) {
    fVar11 = 0.0;
    fVar14 = 0.0;
    if ((ulong)puVar7[5] != 0) {
      fVar14 = *(float *)((long)piVar4 + (ulong)puVar7[5]) * DAT_7100f46f90;
    }
    fVar14 = fVar14 / DAT_7100f46f94;
    if (uVar2 < 0xd) {
      fVar17 = 0.0;
    }
    else {
      fVar17 = 0.0;
      fVar11 = 0.0;
      if ((ulong)puVar7[6] != 0) {
        fVar11 = *(float *)((long)piVar4 + (ulong)puVar7[6]) * DAT_7100f46f90;
      }
      fVar11 = fVar11 / DAT_7100f46f94;
      if ((0xe < uVar2) && ((ulong)puVar7[7] != 0)) {
        fVar17 = *(float *)((long)piVar4 + (ulong)puVar7[7]) * DAT_7100f46f90;
      }
    }
  }
  uVar12 = 0;
  uVar5 = 0;
  uVar9 = 0;
  param_1[0x89] = (ulong)(uint)(fVar17 / DAT_7100f46f94);
  param_1[0x88] = CONCAT44(fVar11,fVar14);
  puVar7 = (ushort *)((long)param_4 - (long)*param_4);
  uVar2 = *puVar7;
  if (0x14 < uVar2) {
    uVar12 = 0;
    uVar9 = 0;
    if ((ulong)puVar7[10] != 0) {
      uVar9 = *(undefined4 *)((long)param_4 + (ulong)puVar7[10]);
    }
    if (uVar2 < 0x17) {
      uVar5 = 0;
    }
    else {
      uVar5 = 0;
      uVar12 = 0;
      if ((ulong)puVar7[0xb] != 0) {
        uVar12 = *(undefined4 *)((long)param_4 + (ulong)puVar7[0xb]);
      }
      if ((0x18 < uVar2) && ((ulong)puVar7[0xc] != 0)) {
        uVar5 = (ulong)*(uint *)((long)param_4 + (ulong)puVar7[0xc]);
      }
    }
  }
  param_1[0x8b] = uVar5;
  param_1[0x8a] = CONCAT44(uVar12,uVar9);
  uVar12 = 0;
  if (0x12 < *(ushort *)((long)param_4 - (long)*param_4)) {
    uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[9];
    uVar12 = 0;
    if (uVar5 != 0) {
      uVar12 = *(undefined4 *)((long)param_4 + uVar5);
    }
  }
  *(undefined4 *)(param_1 + 0x8c) = uVar12;
  if ((0x1a < *(ushort *)((long)param_4 - (long)*param_4)) &&
     (uVar5 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[0xd], uVar5 != 0)) {
    uVar8 = *(undefined4 *)((long)param_4 + uVar5);
  }
  *(undefined4 *)((long)param_1 + 0x464) = uVar8;
  return;
}

