
void FUN_71002334d0(undefined8 *param_1,long *param_2,long *param_3,int *param_4)

{
  undefined *puVar1;
  uint *puVar2;
  undefined8 uVar3;
  undefined *puVar4;
  bool bVar5;
  int iVar6;
  long lVar7;
  undefined8 *puVar8;
  long *plVar9;
  undefined8 *puVar10;
  int *piVar11;
  ulong uVar12;
  long lVar13;
  long lVar14;
  long lVar15;
  long *plVar16;
  long *plVar17;
  undefined4 uVar18;
  
  if ((*(ushort *)((long)param_4 - (long)*param_4) < 5) ||
     (uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[2], uVar12 == 0)) {
    piVar11 = (int *)0x0;
  }
  else {
    puVar2 = (uint *)((long)param_4 + uVar12);
    piVar11 = (int *)((long)puVar2 + (ulong)*puVar2);
  }
  FUN_710026f930(param_1,param_2,param_3,piVar11);
  param_1[0x165] = 0;
  puVar1 = PTR_DAT_71015fe9d8;
  param_1[0x164] = 0;
  param_1[0x163] = 0;
  param_1[0x162] = 0;
  param_1[9] = puVar1 + 0x138;
  param_1[10] = puVar1 + 0x170;
  *param_1 = puVar1 + 0x10;
  param_1[0x155] = 0;
  uVar18 = 0;
  param_1[0x154] = 0;
  param_1[0x153] = 0;
  param_1[0x152] = 0;
  param_1[0x151] = 0;
  puVar1 = PTR_DAT_71015fbbf8 + 0x10;
  param_1[0x150] = puVar1;
  param_1[0x174] = puVar1;
  param_1[0x198] = puVar1;
  *(undefined4 *)(param_1 + 0x1bb) = 0x3f800000;
  param_1[0x1bc] = puVar1;
  *(undefined4 *)(param_1 + 0x1df) = 0x3f800000;
  param_1[0x172] = 0;
  param_1[0x189] = 0;
  param_1[0x188] = 0;
  param_1[0x187] = 0;
  param_1[0x186] = 0;
  param_1[0x179] = 0;
  param_1[0x178] = 0;
  param_1[0x177] = 0;
  param_1[0x176] = 0;
  param_1[0x175] = 0;
  param_1[0x196] = 0;
  param_1[0x1ad] = 0;
  param_1[0x1ac] = 0;
  param_1[0x1ab] = 0;
  param_1[0x1aa] = 0;
  param_1[0x19d] = 0;
  param_1[0x19c] = 0;
  param_1[0x19b] = 0;
  param_1[0x19a] = 0;
  param_1[0x199] = 0;
  param_1[0x1ba] = 0;
  param_1[0x1d1] = 0;
  param_1[0x1d0] = 0;
  param_1[0x1cf] = 0;
  param_1[0x1ce] = 0;
  param_1[0x1c1] = 0;
  param_1[0x1c0] = 0;
  param_1[0x1bf] = 0;
  param_1[0x1be] = 0;
  param_1[0x1bd] = 0;
  param_1[0x1de] = 0;
  *(undefined1 *)((long)param_1 + 0xf0a) = 0;
  *(undefined2 *)(param_1 + 0x1e1) = 0;
  param_1[0x1e0] = 0;
  *(undefined4 *)((long)param_1 + 0xf0c) = 1;
  *(undefined4 *)(param_1 + 0x1e2) = 0;
  *(undefined4 *)((long)param_1 + 0xf14) = 2;
  *(undefined4 *)(param_1 + 0x1e6) = 0;
  param_1[0x1e5] = 0;
  param_1[0x1e4] = 0;
  param_1[0x1e3] = 0;
  if ((6 < *(ushort *)((long)param_4 - (long)*param_4)) &&
     (uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[3], uVar12 != 0)) {
    uVar18 = *(undefined4 *)((long)param_4 + uVar12);
  }
  param_1[0x1e7] = 0xcbf29ce484222645;
  *(undefined4 *)((long)param_1 + 0xf34) = uVar18;
  param_1[0x1ea] = 0;
  param_1[0x1e9] = 0;
  param_1[0x1e8] = 0;
  *(undefined2 *)(param_1 + 0x1eb) = 1;
  *(undefined1 *)((long)param_1 + 0x108f) = 1;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 9) {
    uVar18 = 0;
  }
  else {
    uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[4];
    uVar18 = 0;
    if (uVar12 != 0) {
      uVar18 = *(undefined4 *)((long)param_4 + uVar12);
    }
  }
  *(undefined4 *)(param_1 + 0x212) = uVar18;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 0xb) {
    uVar18 = 0;
  }
  else {
    uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[5];
    uVar18 = 0;
    if (uVar12 != 0) {
      uVar18 = *(undefined4 *)((long)param_4 + uVar12);
    }
  }
  *(undefined4 *)((long)param_1 + 0x1094) = uVar18;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 0xd) {
    uVar18 = 0;
  }
  else {
    uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[6];
    uVar18 = 0;
    if (uVar12 != 0) {
      uVar18 = *(undefined4 *)((long)param_4 + uVar12);
    }
  }
  *(undefined4 *)(param_1 + 0x213) = uVar18;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 0xf) {
    uVar18 = 0;
  }
  else {
    uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[7];
    uVar18 = 0;
    if (uVar12 != 0) {
      uVar18 = *(undefined4 *)((long)param_4 + uVar12);
    }
  }
  *(undefined4 *)((long)param_1 + 0x109c) = uVar18;
  if (*(ushort *)((long)param_4 - (long)*param_4) < 0x11) {
    bVar5 = false;
  }
  else {
    uVar12 = (ulong)((ushort *)((long)param_4 - (long)*param_4))[8];
    bVar5 = false;
    if (uVar12 != 0) {
      bVar5 = *(char *)((long)param_4 + uVar12) != '\0';
    }
  }
  *(bool *)(param_1 + 0x214) = bVar5;
  *(undefined1 *)((long)param_1 + 0x10a1) = 0;
  uVar3 = *(undefined8 *)(PTR_DAT_71015fad58 + 8);
  param_1[0x216] = *(undefined8 *)PTR_DAT_71015fad58;
  param_1[0x217] = uVar3;
  *(undefined1 *)(param_1 + 0x218) = 0;
  *(undefined4 *)((long)param_1 + 0x10c4) = 0;
  param_1[0x219] = 0;
  lVar7 = nn::os::GetTlsValue(*(undefined4 *)PTR_DAT_71015fad18);
  if (0xf < *(ulong *)(lVar7 + 0x80)) {
                    /* WARNING: Subroutine does not return */
    abort();
  }
  *(long **)(lVar7 + *(ulong *)(lVar7 + 0x80) * 8) = param_2;
  *(long *)(lVar7 + 0x80) = *(long *)(lVar7 + 0x80) + 1;
  puVar8 = (undefined8 *)(**(code **)(*param_2 + 0x10))(param_2,0xa8,8);
  if (puVar8 == (undefined8 *)0x0) {
    (**(code **)(*param_2 + 0x90))(param_2);
  }
  FUN_710016f940(puVar8,0,0x14);
  puVar8[1] = param_2;
  puVar8[2] = puVar8;
  puVar8[3] = 0xa8;
  puVar8[4] = 8;
  *(long *)(lVar7 + 0x80) = *(long *)(lVar7 + 0x80) + -1;
  if (puVar8 != (undefined8 *)0x0) {
    (**(code **)(puVar8[9] + 0x10))();
  }
  if (param_1[0x219] != 0) {
    (**(code **)(*(long *)(param_1[0x219] + 0x48) + 0x18))();
    param_1[0x219] = 0;
  }
  param_1[0x219] = puVar8;
  *(undefined1 *)(param_1 + 0x5e) = 1;
  puVar1 = PTR_DAT_71015fad08;
  *(undefined4 *)((long)param_1 + 0x2f4) = 4;
  lVar7 = *(long *)(*(long *)puVar1 + 0x98);
  if (lVar7 != 0) {
    (**(code **)(*(long *)(lVar7 + 0x48) + 0x10))();
  }
  lVar14 = *(long *)(lVar7 + 0x90);
  if (lVar14 != 0) {
    (**(code **)(*(long *)(lVar14 + 0x48) + 0x10))();
  }
  puVar4 = PTR_DAT_71015fcbe0;
  puVar1 = PTR_DAT_71015fcbd8;
  if (*(long *)(lVar14 + 0x138) != 0) {
    plVar16 = *(long **)(lVar14 + 0x130);
    plVar17 = plVar16 + *(long *)(lVar14 + 0x138);
    do {
      do {
        lVar15 = *plVar16;
        puVar8 = (undefined8 *)(lVar15 + 0x50);
        plVar9 = (long *)(**(code **)*puVar8)(puVar8);
        if (((*puVar1 & 1) == 0) && (iVar6 = __cxa_guard_acquire(puVar1), iVar6 != 0)) {
          puVar10 = FUN_7100139cc0();
          *(undefined8 **)puVar4 = puVar10;
          __cxa_guard_release(puVar1);
        }
        for (; plVar9 != (long *)0x0; plVar9 = (long *)*plVar9) {
          if (plVar9 == (long *)puVar4) {
            if ((puVar8 != (undefined8 *)&DAT_00000050) && (*(int *)(lVar15 + 0xb20) == 0))
            goto LAB_710023394c;
            break;
          }
        }
        plVar16 = plVar16 + 1;
      } while (plVar16 != plVar17);
LAB_710023394c:
      lVar15 = *(long *)(lVar14 + 0x130);
      lVar13 = *(long *)(lVar14 + 0x138);
      if ((long *)(lVar15 + lVar13 * 8) != plVar16) {
        uVar12 = (**(code **)(*(long *)*plVar16 + 0x78))();
        if ((uVar12 & 1) == 0) {
          lVar15 = *plVar16;
          if (lVar15 != 0) {
            (**(code **)(*(long *)(lVar15 + 0x48) + 0x10))();
          }
          goto LAB_7100233988;
        }
        lVar15 = *(long *)(lVar14 + 0x130);
        lVar13 = *(long *)(lVar14 + 0x138);
        plVar16 = plVar16 + 1;
      }
      plVar17 = (long *)(lVar15 + lVar13 * 8);
    } while (plVar17 != plVar16);
  }
  lVar15 = 0;
LAB_7100233988:
  FUN_710016d8b0(param_1[0x219],*(undefined8 *)(*(long *)(lVar15 + 0xc80) + 0x90));
  FUN_710016d9d0(param_1[0x219],(long)param_1);
  FUN_710016d830(param_1[0x219],1);
  if (lVar15 != 0) {
    (**(code **)(*(long *)(lVar15 + 0x48) + 0x18))((long *)(lVar15 + 0x48));
  }
  (**(code **)(*(long *)(lVar14 + 0x48) + 0x18))((long *)(lVar14 + 0x48));
  if (lVar7 == 0) {
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x0071002339fc. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (**(code **)(*(long *)(lVar7 + 0x48) + 0x18))((long *)(lVar7 + 0x48));
  return;
}

