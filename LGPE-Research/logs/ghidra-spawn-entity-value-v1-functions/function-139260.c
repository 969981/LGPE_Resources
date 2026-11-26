
undefined8 * FUN_7100139260(void)

{
  int iVar1;
  undefined8 *puVar2;
  
  if (((*PTR_DAT_71015fcc48 & 1) == 0) &&
     (iVar1 = __cxa_guard_acquire(PTR_DAT_71015fcc48), iVar1 != 0)) {
    if (((*PTR_DAT_71015fcc50 & 1) == 0) &&
       (iVar1 = __cxa_guard_acquire(PTR_DAT_71015fcc50), iVar1 != 0)) {
      if (((*PTR_DAT_71015fcc58 & 1) == 0) &&
         (iVar1 = __cxa_guard_acquire(PTR_DAT_71015fcc58), iVar1 != 0)) {
        if (((*PTR_DAT_71015fcba8 & 1) == 0) &&
           (iVar1 = __cxa_guard_acquire(PTR_DAT_71015fcba8), iVar1 != 0)) {
          puVar2 = FUN_71000ad5e0();
          *(undefined8 **)PTR_DAT_71015fcbb0 = puVar2;
          __cxa_guard_release(PTR_DAT_71015fcba8);
        }
        *(undefined **)PTR_DAT_71015fcc60 = PTR_DAT_71015fcbb0;
        __cxa_guard_release(PTR_DAT_71015fcc58);
      }
      *(undefined **)PTR_DAT_71015fcc68 = PTR_DAT_71015fcc60;
      __cxa_guard_release(PTR_DAT_71015fcc50);
    }
    *(undefined **)PTR_DAT_71015fcc70 = PTR_DAT_71015fcc68;
    __cxa_guard_release(PTR_DAT_71015fcc48);
  }
  return (undefined8 *)PTR_DAT_71015fcc70;
}

