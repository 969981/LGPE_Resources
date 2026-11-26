
undefined8 FUN_71002fd8a0(undefined8 param_1,long *param_2)

{
  bool bVar1;
  byte *pbVar2;
  undefined *puVar3;
  undefined *puVar4;
  undefined *puVar5;
  undefined *puVar6;
  bool bVar7;
  int iVar8;
  long *plVar9;
  undefined8 *puVar10;
  ulong uVar11;
  long lVar12;
  long lVar13;
  undefined8 uVar14;
  long lVar15;
  undefined8 *puVar16;
  long *plVar17;
  long lVar18;
  long lVar19;
  long *plVar20;
  long lVar21;
  long lVar22;
  undefined8 local_c8;
  ulong local_c0;
  int local_b4;
  long local_88;
  long local_80;
  long local_78;
  long local_70;
  long local_68;
  
  lVar19 = *(long *)(*param_2 + 0x98);
  if (lVar19 != 0) {
    (**(code **)(*(long *)(lVar19 + 0x48) + 0x10))();
  }
  lVar13 = *(long *)(lVar19 + 0x90);
  if (lVar13 != 0) {
    (**(code **)(*(long *)(lVar13 + 0x48) + 0x10))();
  }
  puVar5 = PTR_DAT_71015fcbe0;
  puVar4 = PTR_DAT_71015fcbd8;
  if (*(long *)(lVar13 + 0x138) == 0) {
    lVar15 = 0;
    lVar22 = 0;
    lVar18 = *(long *)(*param_2 + 0x68);
  }
  else {
    plVar17 = *(long **)(lVar13 + 0x130);
    plVar20 = plVar17 + *(long *)(lVar13 + 0x138);
    do {
      do {
        lVar15 = *plVar17;
        puVar16 = (undefined8 *)(lVar15 + 0x50);
        plVar9 = (long *)(**(code **)*puVar16)(puVar16);
        if (((*puVar4 & 1) == 0) && (iVar8 = __cxa_guard_acquire(puVar4), iVar8 != 0)) {
          puVar10 = FUN_7100139cc0();
          *(undefined8 **)puVar5 = puVar10;
          __cxa_guard_release(puVar4);
        }
        for (; plVar9 != (long *)0x0; plVar9 = (long *)*plVar9) {
          if (plVar9 == (long *)puVar5) {
            if ((puVar16 != (undefined8 *)&DAT_00000050) && (*(int *)(lVar15 + 0xb20) == 0))
            goto LAB_71002fd988;
            break;
          }
        }
        plVar17 = plVar17 + 1;
      } while (plVar17 != plVar20);
LAB_71002fd988:
      lVar15 = *(long *)(lVar13 + 0x130);
      lVar18 = *(long *)(lVar13 + 0x138);
      if ((long *)(lVar15 + lVar18 * 8) != plVar17) {
        uVar11 = (**(code **)(*(long *)*plVar17 + 0x78))();
        if ((uVar11 & 1) == 0) {
          lVar22 = *plVar17;
          if (lVar22 != 0) {
            (**(code **)(*(long *)(lVar22 + 0x48) + 0x10))();
          }
          lVar15 = *(long *)(lVar13 + 0x138);
          pbVar2 = PTR_DAT_71015fcbc8;
          puVar16 = (undefined8 *)PTR_DAT_71015fcbd0;
          goto joined_r0x0071002fda04;
        }
        lVar15 = *(long *)(lVar13 + 0x130);
        lVar18 = *(long *)(lVar13 + 0x138);
        plVar17 = plVar17 + 1;
      }
      plVar20 = (long *)(lVar15 + lVar18 * 8);
    } while (plVar20 != plVar17);
    lVar22 = 0;
    lVar15 = *(long *)(lVar13 + 0x138);
    pbVar2 = PTR_DAT_71015fcbc8;
    puVar16 = (undefined8 *)PTR_DAT_71015fcbd0;
joined_r0x0071002fda04:
    PTR_DAT_71015fcbc8 = pbVar2;
    PTR_DAT_71015fcbd0 = (undefined *)puVar16;
    if (lVar15 == 0) {
      lVar15 = 0;
LAB_71002fdae0:
      lVar18 = *(long *)(*param_2 + 0x68);
    }
    else {
      plVar17 = *(long **)(lVar13 + 0x130);
      plVar20 = plVar17 + lVar15;
      do {
        do {
          lVar15 = *plVar17;
          plVar9 = (long *)(*(code *)**(undefined8 **)(lVar15 + 0x50))
                                     ((undefined8 *)(lVar15 + 0x50));
          if (((*pbVar2 & 1) == 0) && (iVar8 = __cxa_guard_acquire(pbVar2), iVar8 != 0)) {
            puVar10 = FUN_7100139260();
            *puVar16 = puVar10;
            __cxa_guard_release(pbVar2);
          }
          for (; plVar9 != (long *)0x0; plVar9 = (long *)*plVar9) {
            if (plVar9 == puVar16) {
              if ((lVar15 != 0) && (iVar8 = FUN_7100262730(lVar15), iVar8 == 0))
              goto LAB_71002fda90;
              break;
            }
          }
          plVar17 = plVar17 + 1;
        } while (plVar17 != plVar20);
LAB_71002fda90:
        lVar15 = *(long *)(lVar13 + 0x130);
        lVar18 = *(long *)(lVar13 + 0x138);
        if ((long *)(lVar15 + lVar18 * 8) != plVar17) {
          uVar11 = (**(code **)(*(long *)*plVar17 + 0x78))();
          if ((uVar11 & 1) == 0) {
            lVar15 = *plVar17;
            if (((lVar15 == 0) ||
                ((**(code **)(*(long *)(lVar15 + 0x48) + 0x10))((long *)(lVar15 + 0x48)),
                *(int *)(lVar15 + 0xa80) == 0)) ||
               (FUN_710026ecb0(&local_68,lVar15 + 0x1e0), local_68 == 0)) goto LAB_71002fdae0;
            (**(code **)(*(long *)(local_68 + 0x48) + 0x18))();
            uVar14 = 0;
            goto LAB_71002fddec;
          }
          lVar15 = *(long *)(lVar13 + 0x130);
          lVar18 = *(long *)(lVar13 + 0x138);
          plVar17 = plVar17 + 1;
        }
        plVar20 = (long *)(lVar15 + lVar18 * 8);
      } while (plVar20 != plVar17);
      lVar15 = 0;
      lVar18 = *(long *)(*param_2 + 0x68);
    }
  }
  if (lVar18 != 0) {
    (**(code **)(*(long *)(lVar18 + 0x48) + 0x10))();
  }
  FUN_710013f200(*(long *)PTR_DAT_71015faea0,0);
  puVar6 = PTR_DAT_71015fd588;
  puVar5 = PTR_DAT_71015fcbc0;
  puVar4 = PTR_DAT_71015fcbb8;
  if (*(long *)(lVar13 + 0x138) == 0) {
    uVar14 = 0;
  }
  else {
    bVar1 = false;
    local_b4 = 0;
    local_88 = 0;
    plVar17 = *(long **)(lVar13 + 0x130);
    local_c8 = 0xcbf29ce484222645;
    local_c0 = 0xcbf29ce484222645;
    do {
      puVar16 = (undefined8 *)(**(code **)(*(long *)*plVar17 + 0x78))();
      if (((ulong)puVar16 & 1) == 0) {
        lVar21 = *plVar17;
        puVar10 = (undefined8 *)
                  (*(code *)**(undefined8 **)(lVar21 + 0x50))((undefined8 *)(lVar21 + 0x50));
        puVar16 = puVar10;
        if (((*puVar4 & 1) == 0) &&
           (puVar16 = (undefined8 *)__cxa_guard_acquire(puVar4), (int)puVar16 != 0)) {
          puVar16 = FUN_7100139260();
          *(undefined8 **)puVar5 = puVar16;
          puVar16 = (undefined8 *)__cxa_guard_release(puVar4);
        }
        if (puVar10 != (undefined8 *)0x0) {
LAB_71002fdc34:
          if (puVar10 != (undefined8 *)puVar5) goto code_r0x0071002fdc3c;
          if ((lVar21 != 0) && (lVar12 = *(long *)(lVar21 + 0xf48), lVar12 != 0)) {
            plVar20 = (long *)(lVar12 + 0x48);
            (**(code **)(*plVar20 + 0x10))(plVar20);
            if (*(int *)(lVar12 + 0x54) != 0) {
              puVar16 = *(undefined8 **)(lVar12 + 0x60);
              plVar9 = (long *)(**(code **)*puVar16)(puVar16);
              if (((*PTR_DAT_71015fd580 & 1) == 0) &&
                 (iVar8 = __cxa_guard_acquire(PTR_DAT_71015fd580), iVar8 != 0)) {
                if (((*PTR_DAT_71015fadc0 & 1) == 0) &&
                   (iVar8 = __cxa_guard_acquire(), puVar3 = PTR_DAT_71015fadc0, iVar8 != 0)) {
                  *(undefined8 *)PTR_DAT_71015fadc8 = 0;
                  __cxa_guard_release(puVar3);
                }
                *(undefined **)puVar6 = PTR_DAT_71015fadc8;
                __cxa_guard_release(PTR_DAT_71015fd580);
              }
              for (; plVar9 != (long *)puVar6; plVar9 = (long *)*plVar9) {
              }
              if ((puVar16[0x22] != 0) && (bVar7 = FUN_7100238690(lVar21), !bVar7)) {
                uVar11 = FUN_7100238710(lVar21);
                puVar16 = (undefined8 *)(**(code **)(*plVar20 + 0x18))(plVar20);
                if ((uVar11 & 1) == 0) {
                  local_c8 = *(undefined8 *)(lVar21 + 0x188);
                  local_c0 = *(ulong *)(lVar21 + 400);
                  local_b4 = *(int *)(lVar21 + 0xf30);
                  (**(code **)(*(long *)(lVar21 + 0x48) + 0x10))();
                  puVar16 = (undefined8 *)0x0;
                  if (local_88 != 0) {
                    puVar16 = (undefined8 *)(**(code **)(*(long *)(local_88 + 0x48) + 0x18))();
                  }
                  *(undefined1 *)(lVar21 + 0xf58) = 0;
                  bVar1 = true;
                  local_88 = lVar21;
                }
                goto LAB_71002fdd38;
              }
            }
            puVar16 = (undefined8 *)(**(code **)(*plVar20 + 0x18))(plVar20);
          }
        }
      }
LAB_71002fdd38:
      plVar17 = plVar17 + 1;
    } while ((long *)(*(long *)(lVar13 + 0x130) + *(long *)(lVar13 + 0x138) * 8) != plVar17);
    if (bVar1) {
      if (local_b4 == 3) {
        FUN_710017a750(&local_70,local_c0,local_c8,0,0,0,0);
        if (local_70 == 0) {
          uVar14 = 1;
          local_70 = 0;
        }
        else {
          (**(code **)(*(long *)(local_70 + 0x48) + 0x18))();
          local_70 = 0;
          uVar14 = 1;
        }
      }
      else {
        local_78 = local_88;
        if (local_88 == 0) {
          uVar14 = FUN_7100305790(&local_68,puVar16,&local_78);
        }
        else {
          plVar17 = (long *)(local_88 + 0x48);
          uVar14 = (**(code **)(*plVar17 + 0x10))(plVar17);
          FUN_7100305790(&local_68,uVar14,&local_78);
          uVar14 = (**(code **)(*plVar17 + 0x18))(plVar17);
          local_78 = 0;
        }
        local_80 = local_68;
        if (local_68 == 0) {
          FUN_7100305970(uVar14,param_2,&local_80,*(undefined8 *)(local_88 + 0xf38),
                         *(undefined4 *)(local_88 + 0xf30));
        }
        else {
          plVar17 = (long *)(local_68 + 0x48);
          uVar14 = (**(code **)(*plVar17 + 0x10))(plVar17);
          FUN_7100305970(uVar14,param_2,&local_80,*(undefined8 *)(local_88 + 0xf38),
                         *(undefined4 *)(local_88 + 0xf30));
          (**(code **)(*plVar17 + 0x18))(plVar17);
          local_80 = 0;
        }
        if (local_68 != 0) {
          (**(code **)(*(long *)(local_68 + 0x48) + 0x18))();
          local_68 = 0;
        }
        uVar14 = 6;
      }
    }
    else {
      uVar14 = 0;
    }
    if (local_88 != 0) {
      (**(code **)(*(long *)(local_88 + 0x48) + 0x18))((long *)(local_88 + 0x48));
    }
  }
  if (lVar18 != 0) {
    (**(code **)(*(long *)(lVar18 + 0x48) + 0x18))((long *)(lVar18 + 0x48));
  }
  if (lVar15 != 0) {
LAB_71002fddec:
    (**(code **)(*(long *)(lVar15 + 0x48) + 0x18))((long *)(lVar15 + 0x48));
  }
  if (lVar22 != 0) {
    (**(code **)(*(long *)(lVar22 + 0x48) + 0x18))((long *)(lVar22 + 0x48));
  }
  (**(code **)(*(long *)(lVar13 + 0x48) + 0x18))((long *)(lVar13 + 0x48));
  if (lVar19 != 0) {
    (**(code **)(*(long *)(lVar19 + 0x48) + 0x18))((long *)(lVar19 + 0x48));
  }
  return uVar14;
code_r0x0071002fdc3c:
  puVar10 = (undefined8 *)*puVar10;
  if (puVar10 == (undefined8 *)0x0) goto LAB_71002fdd38;
  goto LAB_71002fdc34;
}

