
ulong FUN_71002f8a50(long param_1,long *param_2)

{
  byte bVar1;
  bool bVar2;
  uint uVar3;
  ulong uVar4;
  long lVar5;
  long *plVar6;
  long lVar7;
  ulong unaff_x23;
  int local_60 [6];
  long local_48;
  
  lVar5 = *(long *)(*(long *)(param_1 + 0x60) + 0xe0);
  if (lVar5 == 0) {
    uVar4 = FUN_7100179400(0);
  }
  else {
    plVar6 = (long *)(lVar5 + 0x48);
    (**(code **)(*plVar6 + 0x10))(plVar6);
    uVar4 = FUN_7100179400(lVar5);
    (**(code **)(*plVar6 + 0x18))(plVar6);
  }
  if ((uVar4 & 1) == 0) {
    lVar5 = *(long *)(*(long *)(param_1 + 0x60) + 0xe0);
    if (lVar5 == 0) {
      uVar4 = FUN_71001792a0(0);
    }
    else {
      plVar6 = (long *)(lVar5 + 0x48);
      (**(code **)(*plVar6 + 0x10))(plVar6);
      uVar4 = FUN_71001792a0(lVar5);
      (**(code **)(*plVar6 + 0x18))(plVar6);
    }
    if ((uVar4 & 1) == 0) {
      lVar5 = *(long *)(*param_2 + 0x98);
      if (lVar5 != 0) {
        (**(code **)(*(long *)(lVar5 + 0x48) + 0x10))();
      }
      lVar7 = *(long *)(lVar5 + 0xb8);
      if (lVar7 != 0) {
        (**(code **)(*(long *)(lVar7 + 0x48) + 0x10))();
      }
      if (((((((*(long *)(lVar7 + 0x288) == 0x194d955fbf0a7685) ||
              (*(long *)(lVar7 + 0x290) == 0x194d955fbf0a7685)) ||
             (*(long *)(lVar7 + 0x298) == 0x194d955fbf0a7685)) ||
            ((*(long *)(lVar7 + 0x2a0) == 0x194d955fbf0a7685 ||
             (*(long *)(lVar7 + 0x2a8) == 0x194d955fbf0a7685)))) ||
           (((*(long *)(lVar7 + 0x2b0) == 0x194d955fbf0a7685 ||
             ((*(long *)(lVar7 + 0x2b8) == 0x194d955fbf0a7685 ||
              (*(long *)(lVar7 + 0x2c0) == 0x194d955fbf0a7685)))) ||
            (*(long *)(lVar7 + 0x2c8) == 0x194d955fbf0a7685)))) ||
          ((((*(long *)(lVar7 + 0x2d0) == 0x194d955fbf0a7685 ||
             (*(long *)(lVar7 + 0x288) == -0x279ad54afd4bdd39)) ||
            (*(long *)(lVar7 + 0x290) == -0x279ad54afd4bdd39)) ||
           (((*(long *)(lVar7 + 0x298) == -0x279ad54afd4bdd39 ||
             (*(long *)(lVar7 + 0x2a0) == -0x279ad54afd4bdd39)) ||
            ((*(long *)(lVar7 + 0x2a8) == -0x279ad54afd4bdd39 ||
             ((*(long *)(lVar7 + 0x2b0) == -0x279ad54afd4bdd39 ||
              (*(long *)(lVar7 + 0x2b8) == -0x279ad54afd4bdd39)))))))))) ||
         ((*(long *)(lVar7 + 0x2c0) == -0x279ad54afd4bdd39 ||
          ((*(long *)(lVar7 + 0x2c8) == -0x279ad54afd4bdd39 ||
           (*(long *)(lVar7 + 0x2d0) == -0x279ad54afd4bdd39)))))) {
        uVar4 = FUN_71002f8e70(param_1,param_2);
        unaff_x23 = uVar4 & 0xffffffff;
        bVar2 = false;
      }
      else {
        bVar2 = true;
      }
      (**(code **)(*(long *)(lVar7 + 0x48) + 0x18))((long *)(lVar7 + 0x48));
      (**(code **)(*(long *)(lVar5 + 0x48) + 0x18))((long *)(lVar5 + 0x48));
      if (bVar2) {
        uVar4 = FUN_71002f9550(param_1,param_2);
        unaff_x23 = uVar4 & 0xffffffff;
        if ((int)uVar4 == 0) {
          if ((*(byte *)(param_2 + 3) & 0x30) == 0) {
            uVar3 = FUN_71002f9bf0(param_1,param_2);
            unaff_x23 = (ulong)uVar3;
            if (uVar3 != 0) goto LAB_71002f8cdc;
          }
          uVar3 = FUN_71002fa700(param_1,param_2);
          unaff_x23 = (ulong)uVar3;
          if (uVar3 == 0) {
            uVar4 = FUN_71002fab90(param_1,param_2);
            unaff_x23 = uVar4 & 0xffffffff;
            if ((int)uVar4 == 0) {
              bVar1 = *(byte *)(param_2 + 3);
              if ((bVar1 & 1) != 0) {
                uVar3 = FUN_71002fc0c0(param_1,param_2);
                unaff_x23 = (ulong)uVar3;
                if (uVar3 != 0) goto LAB_71002f8cdc;
                bVar1 = *(byte *)(param_2 + 3);
              }
              if ((bVar1 >> 1 & 1) == 0) {
                if (-1 < (char)bVar1) {
                  if ((bVar1 >> 4 & 1) != 0) {
                    uVar4 = FUN_71002fd370(param_1,param_2);
                    unaff_x23 = uVar4 & 0xffffffff;
                    if ((int)uVar4 != 0) goto LAB_71002f8cdc;
                    bVar1 = *(byte *)(param_2 + 3);
                  }
                  if ((bVar1 >> 5 & 1) != 0) {
                    uVar4 = FUN_71002fd570(param_1,param_2);
                    unaff_x23 = uVar4 & 0xffffffff;
                    if ((int)uVar4 != 0) goto LAB_71002f8cdc;
                  }
                  local_60[0] = 0;
                  uVar4 = FUN_7100303af0(param_1,param_2,local_60);
                  if ((uVar4 & 1) == 0) {
                    local_60[0] = 1;
                    uVar4 = FUN_7100303af0(param_1,param_2,local_60);
                    if ((uVar4 & 1) == 0) {
                      local_60[0] = 0;
                      uVar4 = FUN_7100304cd0(param_1,param_2,local_60);
                      if ((uVar4 & 1) == 0) {
                        uVar4 = FUN_71002fd8a0(param_1,param_2);
                        unaff_x23 = uVar4 & 0xffffffff;
                        if ((int)uVar4 == 0) {
                          FUN_71002fdf90(param_1,param_2);
                          FUN_7100300e40(param_1,param_2);
                          if ((*(byte *)(param_2 + 3) & 1) != 0) {
                            uVar3 = FUN_7100301bd0(param_1,param_2);
                            unaff_x23 = (ulong)uVar3;
                            if (uVar3 != 0) goto LAB_71002f8cdc;
                          }
                          FUN_71003024d0(param_1,param_2);
                          return 0;
                        }
                      }
                      else {
                        unaff_x23 = 9;
                      }
                      goto LAB_71002f8cdc;
                    }
                  }
                  unaff_x23 = 8;
                  goto LAB_71002f8cdc;
                }
                FUN_710027ef50(1,*param_2,0);
              }
              else {
                FUN_710033a490(0,*param_2,param_2[2]);
                lVar5 = *(long *)PTR_DAT_71015face8;
                FUN_710001dca0((undefined8 *)local_60,(undefined8 *)&DAT_710154c248);
                FUN_710016e8b0(lVar5,(long)local_60);
                if (local_48 != 0) {
                  (**(code **)(*(long *)(local_48 + 0x48) + 0x18))();
                }
              }
              unaff_x23 = 2;
            }
          }
        }
      }
      goto LAB_71002f8cdc;
    }
  }
  unaff_x23 = 1;
LAB_71002f8cdc:
  return unaff_x23 & 0xffffffff;
}

