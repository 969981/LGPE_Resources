
undefined4 FUN_7100218470(long param_1)

{
  long lVar1;
  long *plVar2;
  undefined4 local_68;
  undefined1 local_64;
  undefined4 local_60;
  undefined2 local_5c;
  undefined4 local_58;
  long local_50;
  undefined8 local_48;
  undefined8 local_40;
  undefined8 local_38;
  
  lVar1 = *(long *)(*(long *)PTR_DAT_71015fad08 + 0x78);
  if (lVar1 == 0) {
    lVar1 = FUN_71000a87a0(0);
  }
  else {
    plVar2 = (long *)(lVar1 + 0x48);
    (**(code **)(*plVar2 + 0x10))(plVar2);
    lVar1 = FUN_71000a87a0(lVar1);
    (**(code **)(*plVar2 + 0x18))(plVar2);
  }
  local_50 = *(long *)(param_1 + 1000);
  local_48 = *(undefined8 *)(param_1 + 0x3f0);
  local_40 = *(undefined8 *)(param_1 + 0x3f8);
  local_38 = *(undefined8 *)(param_1 + 0x400);
  local_68 = 0;
  local_64 = 0;
  local_60 = 0;
  local_58 = 0;
  local_5c = 0;
  FUN_71000d4af0(lVar1,&local_50,&local_68);
  return local_68;
}

