
void FUN_71000b84d0(long *param_1,long *param_2)

{
  int *piVar1;
  long lVar2;
  char cVar3;
  bool bVar4;
  undefined *puVar5;
  undefined *puVar6;
  undefined *puVar7;
  undefined *puVar8;
  int iVar9;
  long lVar10;
  int iVar11;
  long *plVar12;
  
  puVar8 = PTR_DAT_71015fc3c8;
  puVar7 = PTR_DAT_71015fc3c0;
  puVar6 = PTR_DAT_71015fadc8;
  puVar5 = PTR_DAT_71015fadc0;
  lVar10 = *param_2;
  if ((lVar10 != 0) && (*(int *)(lVar10 + 0x54) != 0)) {
    piVar1 = (int *)(lVar10 + 0x54);
    iVar11 = *(int *)(lVar10 + 0x54);
    do {
      while( true ) {
        plVar12 = *(long **)(lVar10 + 0x58);
        if (((*puVar7 & 1) == 0) && (iVar9 = __cxa_guard_acquire(puVar7), iVar9 != 0)) {
          if (((*puVar5 & 1) == 0) && (iVar9 = __cxa_guard_acquire(puVar5), iVar9 != 0)) {
            *(undefined8 *)puVar6 = 0;
            __cxa_guard_release(puVar5);
          }
          *(undefined **)puVar8 = puVar6;
          __cxa_guard_release(puVar7);
        }
        while( true ) {
          if (plVar12 == (long *)0x0) goto LAB_71000b85b0;
          if (plVar12 == (long *)puVar8) break;
          plVar12 = (long *)*plVar12;
        }
        iVar9 = *piVar1;
        if (iVar9 != iVar11) break;
        cVar3 = '\x01';
        bVar4 = (bool)ExclusiveMonitorPass(piVar1,0x10);
        if (bVar4) {
          *piVar1 = iVar11 + 1;
          cVar3 = ExclusiveMonitorsStatus();
        }
        if (cVar3 == '\0') {
          lVar2 = 0;
          if (*(long *)(lVar10 + 0x60) != 0) {
            lVar2 = *(long *)(lVar10 + 0x60) + -0x50;
          }
          *param_1 = lVar2;
          return;
        }
        iVar11 = iVar9;
        if (iVar9 == 0) goto LAB_71000b85b0;
      }
      ClearExclusiveLocal();
      iVar11 = iVar9;
    } while (iVar9 != 0);
  }
LAB_71000b85b0:
  *param_1 = 0;
  return;
}

