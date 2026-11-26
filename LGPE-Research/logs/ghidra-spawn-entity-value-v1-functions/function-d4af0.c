
void FUN_71000d4af0(long param_1,long *param_2,undefined4 *param_3)

{
  uint *puVar1;
  ushort uVar2;
  bool bVar3;
  bool bVar4;
  long *plVar5;
  long *plVar6;
  undefined1 uVar7;
  int iVar8;
  int *piVar9;
  uint *puVar10;
  ulong uVar11;
  undefined4 uVar12;
  ulong uVar13;
  ulong uVar14;
  long lVar15;
  long lVar16;
  long local_78;
  long local_70;
  long local_68;
  long local_60;
  long local_58;
  long local_50;
  long local_48;
  
  plVar6 = (long *)(param_1 + 0x18);
  *param_3 = 0x69;
  *(undefined1 *)(param_3 + 1) = 0;
  param_3[2] = 0;
  *(undefined2 *)(param_3 + 3) = 0;
  param_3[4] = 0;
  FUN_71000b84d0(&local_48,plVar6);
  plVar5 = (long *)FUN_71000d22b0(local_48,0xf);
  lVar15 = *param_2;
  lVar16 = *plVar5;
  if (local_48 != 0) {
    (**(code **)(*(long *)(local_48 + 0x48) + 0x18))();
    local_48 = 0;
  }
  if (lVar15 == lVar16) {
    piVar9 = *(int **)(param_1 + 8);
    uVar11 = (ulong)*(ushort *)((long)piVar9 + (4 - (long)*piVar9));
    puVar1 = (uint *)((long)piVar9 + uVar11);
    uVar14 = (ulong)*puVar1;
    puVar1 = (uint *)((long)puVar1 + uVar14);
    uVar13 = (ulong)*puVar1;
    if (uVar13 != 0) {
      bVar4 = false;
      puVar10 = (uint *)((long)piVar9 + uVar14 + uVar11 + 8);
      do {
        uVar11 = (ulong)puVar10[-1];
        lVar15 = uVar11 - (long)*(int *)((long)puVar10 + (uVar11 - 4));
        uVar2 = *(ushort *)((long)puVar10 + lVar15 + -4);
        if (uVar2 < 5) {
          if (param_2[1] == 0) goto LAB_71000d4bfc;
        }
        else {
          lVar16 = 0;
          if ((ulong)*(ushort *)((long)puVar10 + lVar15) != 0) {
            lVar16 = *(long *)((long)puVar10 + uVar11 + *(ushort *)((long)puVar10 + lVar15) + -4);
          }
          if (lVar16 == param_2[1]) {
LAB_71000d4bfc:
            if (uVar2 < 9) {
              uVar12 = 0;
            }
            else {
              uVar13 = (ulong)*(ushort *)((long)puVar10 + lVar15 + 4);
              uVar12 = 0;
              if (uVar13 != 0) {
                uVar12 = *(undefined4 *)((long)puVar10 + uVar11 + uVar13 + -4);
              }
            }
            *param_3 = uVar12;
            *(undefined1 *)(param_3 + 1) = 0;
            uVar11 = (ulong)puVar10[-1];
            lVar15 = uVar11 - (long)*(int *)((long)puVar10 + (uVar11 - 4));
            uVar2 = *(ushort *)((long)puVar10 + lVar15 + -4);
            if ((6 < uVar2) &&
               (uVar13 = (ulong)*(ushort *)((long)puVar10 + lVar15 + 2), uVar13 != 0)) {
              lVar16 = uVar11 + uVar13;
              if (*(long *)((long)puVar10 + lVar16 + -4) == -0x340d631b7bddd9bb) {
LAB_71000d4cdc:
                uVar7 = 0;
              }
              else {
                if (*(long *)((long)puVar10 + lVar16 + -4) != param_2[2]) goto LAB_71000d4c9c;
LAB_71000d4cbc:
                if (uVar2 < 0xb) goto LAB_71000d4cdc;
                uVar13 = (ulong)*(ushort *)((long)puVar10 + lVar15 + 6);
                uVar7 = 0;
                if (uVar13 != 0) {
                  uVar7 = (undefined1)*(undefined4 *)((long)puVar10 + uVar13 + uVar11 + -4);
                }
              }
              *(undefined1 *)(param_3 + 1) = uVar7;
              goto LAB_71000d4ce4;
            }
            if (param_2[2] == 0) goto LAB_71000d4cbc;
LAB_71000d4c9c:
            uVar13 = (ulong)*puVar1;
            bVar4 = true;
          }
        }
        bVar3 = puVar10 != puVar1 + uVar13 + 1;
        puVar10 = puVar10 + 1;
      } while (bVar3);
      if (bVar4) {
LAB_71000d4ce4:
        FUN_71000b84d0(&local_50,plVar6);
        plVar5 = (long *)FUN_71000d22b0(local_50,0x17);
        lVar15 = param_2[3];
        lVar16 = *plVar5;
        if (local_50 != 0) {
          (**(code **)(*(long *)(local_50 + 0x48) + 0x18))();
          local_50 = 0;
        }
        if (lVar15 == lVar16) {
          iVar8 = 0;
          bVar4 = false;
        }
        else {
          FUN_71000b84d0(&local_58,plVar6);
          plVar5 = (long *)FUN_71000d22b0(local_58,0x18);
          lVar15 = param_2[3];
          lVar16 = *plVar5;
          if (local_58 != 0) {
            (**(code **)(*(long *)(local_58 + 0x48) + 0x18))();
            local_58 = 0;
          }
          if (lVar15 == lVar16) {
            iVar8 = 0;
            bVar4 = true;
          }
          else {
            FUN_71000b84d0(&local_60,plVar6);
            plVar5 = (long *)FUN_71000d22b0(local_60,0x19);
            lVar15 = param_2[3];
            lVar16 = *plVar5;
            if (local_60 != 0) {
              (**(code **)(*(long *)(local_60 + 0x48) + 0x18))();
              local_60 = 0;
            }
            if (lVar15 == lVar16) {
              bVar4 = false;
              iVar8 = 1;
            }
            else {
              FUN_71000b84d0(&local_68,plVar6);
              plVar5 = (long *)FUN_71000d22b0(local_68,0x1a);
              lVar15 = param_2[3];
              lVar16 = *plVar5;
              if (local_68 != 0) {
                (**(code **)(*(long *)(local_68 + 0x48) + 0x18))();
                local_68 = 0;
              }
              if (lVar15 == lVar16) {
                iVar8 = 1;
                bVar4 = true;
              }
              else {
                FUN_71000b84d0(&local_70,plVar6);
                plVar5 = (long *)FUN_71000d22b0(local_70,0x1b);
                lVar15 = param_2[3];
                lVar16 = *plVar5;
                if (local_70 != 0) {
                  (**(code **)(*(long *)(local_70 + 0x48) + 0x18))();
                  local_70 = 0;
                }
                if (lVar15 == lVar16) {
                  bVar4 = false;
                  iVar8 = 2;
                }
                else {
                  FUN_71000b84d0(&local_78,plVar6);
                  plVar6 = (long *)FUN_71000d22b0(local_78,0x1c);
                  lVar15 = param_2[3];
                  lVar16 = *plVar6;
                  if (local_78 != 0) {
                    (**(code **)(*(long *)(local_78 + 0x48) + 0x18))();
                  }
                  bVar4 = lVar15 == lVar16;
                  iVar8 = (uint)bVar4 << 1;
                }
              }
            }
          }
        }
        param_3[2] = iVar8;
        *(bool *)(param_3 + 3) = bVar4;
        *(undefined1 *)((long)param_3 + 0xd) = 0;
        param_3[4] = 0;
      }
    }
  }
  return;
}

