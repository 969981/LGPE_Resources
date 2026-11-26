
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_7100300e40(long param_1,long *param_2)

{
  int *piVar1;
  undefined1 auVar2 [16];
  undefined1 auVar3 [16];
  undefined1 auVar4 [16];
  undefined1 auVar5 [16];
  undefined8 uVar6;
  undefined8 uVar7;
  undefined1 auVar8 [16];
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  undefined1 auVar11 [16];
  undefined8 uVar12;
  undefined1 auVar13 [16];
  undefined1 auVar14 [16];
  undefined1 auVar15 [16];
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  undefined1 auVar18 [16];
  undefined *puVar19;
  undefined *puVar20;
  uint *puVar21;
  bool bVar22;
  int iVar23;
  uint uVar24;
  uint uVar25;
  long *plVar26;
  undefined8 *puVar27;
  ulong uVar28;
  long *plVar29;
  uint *puVar30;
  uint *puVar31;
  int iVar32;
  ulong uVar33;
  uint *puVar34;
  uint *puVar35;
  ulong uVar36;
  long lVar37;
  long lVar38;
  long lVar39;
  long *plVar40;
  long lVar41;
  long lVar42;
  undefined8 *puVar43;
  long lVar44;
  uint *puVar45;
  long *plVar46;
  float extraout_s0;
  float fVar47;
  float fVar48;
  undefined8 uVar49;
  undefined1 auVar50 [12];
  float extraout_var;
  float extraout_var_00;
  undefined1 auVar51 [16];
  undefined1 auVar52 [16];
  float fVar59;
  float fVar61;
  undefined1 auVar53 [16];
  undefined1 auVar54 [16];
  undefined1 auVar55 [16];
  undefined1 auVar56 [16];
  float fVar60;
  float fVar62;
  float fVar63;
  undefined1 auVar57 [16];
  undefined1 auVar58 [16];
  float fVar64;
  undefined8 uVar65;
  float fVar70;
  undefined1 auVar66 [16];
  undefined1 auVar67 [16];
  undefined1 auVar68 [16];
  undefined1 auVar69 [16];
  undefined1 auVar71 [16];
  undefined1 auVar72 [16];
  undefined1 auVar73 [16];
  undefined1 auVar74 [16];
  undefined1 auVar75 [16];
  undefined1 auVar76 [16];
  undefined1 auVar77 [16];
  float fVar78;
  float fVar79;
  undefined1 uVar80;
  undefined1 uVar81;
  undefined1 uVar82;
  undefined1 uVar83;
  undefined1 uVar84;
  undefined1 uVar85;
  undefined1 uVar86;
  undefined1 uVar87;
  undefined1 uVar88;
  undefined1 uVar89;
  undefined1 uVar90;
  undefined1 uVar91;
  undefined4 uVar92;
  undefined8 uVar93;
  undefined8 uVar94;
  undefined8 uVar95;
  undefined8 uVar96;
  undefined8 uVar97;
  undefined8 uVar98;
  float fVar99;
  float fVar100;
  float fVar101;
  float fVar102;
  long *local_100;
  undefined8 uStack_f8;
  long alStack_f0 [4];
  long *local_d0;
  long *local_c0;
  long local_b8;
  long local_b0;
  undefined8 auStack_a0 [2];
  long local_90;
  long local_80;
  undefined8 *local_78;
  
  lVar38 = *(long *)(*param_2 + 0x98);
  if (lVar38 != 0) {
    (**(code **)(*(long *)(lVar38 + 0x48) + 0x10))();
  }
  lVar39 = *(long *)(lVar38 + 0xb8);
  if (lVar39 != 0) {
    (**(code **)(*(long *)(lVar39 + 0x48) + 0x10))();
  }
  plVar40 = *(long **)(lVar38 + 0x90);
  if (plVar40 != (long *)0x0) {
    (**(code **)(plVar40[9] + 0x10))();
  }
  lVar41 = *(long *)(*(long *)(lVar38 + 0x58) + 0x68);
  if (lVar41 != 0) {
    (**(code **)(*(long *)(lVar41 + 0x48) + 0x10))();
  }
  puVar20 = PTR_DAT_71015fcbe0;
  puVar19 = PTR_DAT_71015fcbd8;
  if (plVar40[0x27] == 0) {
    lVar42 = 0;
    lVar44 = *(long *)(*(long *)(lVar38 + 0x58) + 0x80);
    if (lVar44 == 0) goto LAB_7100300fc0;
LAB_7100301014:
    plVar46 = (long *)(lVar44 + 0x48);
    (**(code **)(*plVar46 + 0x10))(plVar46);
    bVar22 = FUN_71001c3f10(lVar44,-0x50102d0d697999b6);
    (**(code **)(*plVar46 + 0x18))(plVar46);
  }
  else {
    plVar46 = (long *)plVar40[0x26];
    plVar29 = plVar46 + plVar40[0x27];
    do {
      do {
        lVar42 = *plVar46;
        puVar43 = (undefined8 *)(lVar42 + 0x50);
        plVar26 = (long *)(**(code **)*puVar43)(puVar43);
        if (((*puVar19 & 1) == 0) && (iVar23 = __cxa_guard_acquire(puVar19), iVar23 != 0)) {
          puVar27 = FUN_7100139cc0();
          *(undefined8 **)puVar20 = puVar27;
          __cxa_guard_release(puVar19);
        }
        for (; plVar26 != (long *)0x0; plVar26 = (long *)*plVar26) {
          if (plVar26 == (long *)puVar20) {
            if ((puVar43 != (undefined8 *)&DAT_00000050) && (*(int *)(lVar42 + 0xb20) == 0))
            goto LAB_7100300f70;
            break;
          }
        }
        plVar46 = plVar46 + 1;
      } while (plVar46 != plVar29);
LAB_7100300f70:
      lVar42 = plVar40[0x26];
      lVar44 = plVar40[0x27];
      if ((long *)(lVar42 + lVar44 * 8) != plVar46) {
        uVar28 = (**(code **)(*(long *)*plVar46 + 0x78))();
        if ((uVar28 & 1) == 0) {
          lVar42 = *plVar46;
          if (lVar42 != 0) {
            (**(code **)(*(long *)(lVar42 + 0x48) + 0x10))();
          }
          goto LAB_7100300ff8;
        }
        lVar42 = plVar40[0x26];
        lVar44 = plVar40[0x27];
        plVar46 = plVar46 + 1;
      }
      plVar29 = (long *)(lVar42 + lVar44 * 8);
    } while (plVar29 != plVar46);
    lVar42 = 0;
LAB_7100300ff8:
    lVar44 = *(long *)(*(long *)(lVar38 + 0x58) + 0x80);
    if (lVar44 != 0) goto LAB_7100301014;
LAB_7100300fc0:
    bVar22 = FUN_71001c3f10(0,-0x50102d0d697999b6);
  }
  if (!bVar22) goto joined_r0x007100301bb0;
  local_80 = -0x340d631b7bddd9bb;
  FUN_710024a140(&local_80,1);
  if (local_80 < -0x68214e0d2f57cd7e) {
    if ((local_80 != -0x6821540d2f57d7b0) && (local_80 != -0x68214f0d2f57cf31))
    goto joined_r0x007100301bb0;
  }
  else if ((local_80 != -0x68214d0d2f57cbcb) && (local_80 != -0x68214e0d2f57cd7e))
  goto joined_r0x007100301bb0;
  uVar24 = FUN_71001c95f0(lVar41,0x36a);
  if ((uVar24 != 0) ||
     ((FUN_710065e900(auStack_a0,lVar42 + 0x2c0), local_90 != -0x29cdf4a4d0c3103c &&
      (local_90 != -0x4f7e3d723b7d68d6)))) goto joined_r0x007100301bb0;
  uVar28 = *(ulong *)(param_1 + 0x80);
  uVar33 = *(ulong *)(param_1 + 0x88);
  do {
    uVar36 = uVar28 ^ uVar33;
    iVar32 = (int)uVar33;
    iVar23 = (int)uVar28;
    uVar33 = uVar36 >> 0x1b | uVar36 << 0x25;
    uVar28 = uVar36 ^ (uVar28 >> 0x28 | uVar28 << 0x18) ^ uVar36 << 0x10;
    uVar24 = iVar23 + iVar32 & 0x7f;
  } while (100 < uVar24);
  *(ulong *)(param_1 + 0x80) = uVar28;
  *(ulong *)(param_1 + 0x88) = uVar33;
  uVar25 = FUN_71003154a0(*(undefined8 *)(param_1 + 0x70),local_80,0,0);
  if (uVar25 <= uVar24) goto joined_r0x007100301bb0;
  FUN_7100218c40((undefined8 *)(lVar42 + 0xa0));
  uVar28 = *(ulong *)(param_1 + 0x80);
  uVar33 = *(ulong *)(param_1 + 0x88);
  do {
    uVar36 = uVar28 ^ uVar33;
    iVar32 = (int)uVar33;
    iVar23 = (int)uVar28;
    uVar33 = uVar36 >> 0x1b | uVar36 << 0x25;
    uVar28 = uVar36 ^ (uVar28 >> 0x28 | uVar28 << 0x18) ^ uVar36 << 0x10;
    uVar24 = iVar23 + iVar32 & 0x7f;
  } while (0x78 < uVar24);
  *(ulong *)(param_1 + 0x80) = uVar28;
  *(ulong *)(param_1 + 0x88) = uVar33;
  auVar51 = FUN_7100056ff0(extraout_var +
                           (*(float *)PTR_FloatPi_71015fb690 /
                           *(float *)PTR_FloatDegree180_71015fbc18) * (float)(int)(uVar24 - 0x3c),
                           extraout_s0,extraout_var_00);
  uVar92 = (undefined4)((ulong)*(undefined8 *)(PTR_DAT_71015fd520 + 8) >> 0x20);
  fVar47 = auVar51._0_4_ * (float)_DAT_7100ef92a0;
  fVar59 = auVar51._4_4_ * (float)((ulong)_DAT_7100ef92a0 >> 0x20);
  uVar80 = SUB41(fVar59,0);
  uVar81 = (undefined1)((uint)fVar59 >> 8);
  uVar82 = (undefined1)((uint)fVar59 >> 0x10);
  uVar83 = (undefined1)((uint)fVar59 >> 0x18);
  fVar61 = auVar51._8_4_ * (float)_UNK_7100ef92a8;
  uVar84 = SUB41(fVar61,0);
  uVar85 = (undefined1)((uint)fVar61 >> 8);
  uVar86 = (undefined1)((uint)fVar61 >> 0x10);
  uVar87 = (undefined1)((uint)fVar61 >> 0x18);
  fVar64 = auVar51._12_4_ * (float)((ulong)_UNK_7100ef92a8 >> 0x20);
  uVar88 = SUB41(fVar64,0);
  uVar89 = (undefined1)((uint)fVar64 >> 8);
  uVar90 = (undefined1)((uint)fVar64 >> 0x10);
  uVar91 = (undefined1)((uint)fVar64 >> 0x18);
  auVar8._12_4_ = uVar92;
  auVar8._0_12_ = *(undefined1 (*) [12])PTR_DAT_71015fd520;
  uVar65 = a64_TBL(ZEXT816(0),auVar8,DAT_7100f46628);
  auVar9._12_4_ = uVar92;
  auVar9._0_12_ = *(undefined1 (*) [12])PTR_DAT_71015fd520;
  uVar93 = a64_TBL(ZEXT816(0),auVar9,DAT_7100f46630);
  auVar68[4] = uVar80;
  auVar68._0_4_ = fVar47;
  auVar68[5] = uVar81;
  auVar68[6] = uVar82;
  auVar68[7] = uVar83;
  auVar68[8] = uVar84;
  auVar68[9] = uVar85;
  auVar68[10] = uVar86;
  auVar68[0xb] = uVar87;
  auVar68[0xc] = uVar88;
  auVar68[0xd] = uVar89;
  auVar68[0xe] = uVar90;
  auVar68[0xf] = uVar91;
  uVar96 = a64_TBL(ZEXT816(0),auVar68,DAT_7100f46628);
  fVar70 = (float)((ulong)uVar65 >> 0x20);
  auVar10._12_4_ = uVar92;
  auVar10._0_12_ = *(undefined1 (*) [12])PTR_DAT_71015fd520;
  uVar95 = a64_TBL(ZEXT816(0),auVar10,DAT_7100f465a8);
  auVar76[4] = uVar80;
  auVar76._0_4_ = fVar47;
  auVar76[5] = uVar81;
  auVar76[6] = uVar82;
  auVar76[7] = uVar83;
  auVar76[8] = uVar84;
  auVar76[9] = uVar85;
  auVar76[10] = uVar86;
  auVar76[0xb] = uVar87;
  auVar76[0xc] = uVar88;
  auVar76[0xd] = uVar89;
  auVar76[0xe] = uVar90;
  auVar76[0xf] = uVar91;
  uVar97 = a64_TBL(ZEXT816(0),auVar76,DAT_7100f46638);
  fVar60 = (float)((ulong)uVar93 >> 0x20);
  fVar78 = (float)((ulong)uVar95 >> 0x20);
  fVar48 = (float)_DAT_7100ef92b0;
  fVar62 = (float)((ulong)_DAT_7100ef92b0 >> 0x20);
  fVar63 = (float)_UNK_7100ef92b8;
  fVar79 = (float)((ulong)_UNK_7100ef92b8 >> 0x20);
  auVar11._12_4_ = uVar92;
  auVar11._0_12_ = *(undefined1 (*) [12])PTR_DAT_71015fd520;
  uVar12 = a64_TBL(ZEXT816(0),auVar11,DAT_7100f46598);
  fVar102 = (float)((ulong)uVar12 >> 0x20);
  auVar2[4] = uVar80;
  auVar2._0_4_ = fVar47;
  auVar2[5] = uVar81;
  auVar2[6] = uVar82;
  auVar2[7] = uVar83;
  auVar2[8] = uVar84;
  auVar2[9] = uVar85;
  auVar2[10] = uVar86;
  auVar2[0xb] = uVar87;
  auVar2[0xc] = uVar88;
  auVar2[0xd] = uVar89;
  auVar2[0xe] = uVar90;
  auVar2[0xf] = uVar91;
  uVar94 = a64_TBL(ZEXT816(0),auVar2,DAT_7100f465a8);
  auVar3[4] = uVar80;
  auVar3._0_4_ = fVar47;
  auVar3[5] = uVar81;
  auVar3[6] = uVar82;
  auVar3[7] = uVar83;
  auVar3[8] = uVar84;
  auVar3[9] = uVar85;
  auVar3[10] = uVar86;
  auVar3[0xb] = uVar87;
  auVar3[0xc] = uVar88;
  auVar3[0xd] = uVar89;
  auVar3[0xe] = uVar90;
  auVar3[0xf] = uVar91;
  uVar98 = a64_TBL(ZEXT816(0),auVar3,DAT_7100f46640);
  uVar28 = *(ulong *)(param_1 + 0x80);
  uVar33 = *(ulong *)(param_1 + 0x88);
  auVar4[4] = uVar80;
  auVar4._0_4_ = fVar47;
  auVar4[5] = uVar81;
  auVar4[6] = uVar82;
  auVar4[7] = uVar83;
  auVar4[8] = uVar84;
  auVar4[9] = uVar85;
  auVar4[10] = uVar86;
  auVar4[0xb] = uVar87;
  auVar4[0xc] = uVar88;
  auVar4[0xd] = uVar89;
  auVar4[0xe] = uVar90;
  auVar4[0xf] = uVar91;
  uVar49 = a64_TBL(ZEXT816(0),auVar4,DAT_7100f46598);
  auVar5[4] = uVar80;
  auVar5._0_4_ = fVar47;
  auVar5[5] = uVar81;
  auVar5[6] = uVar82;
  auVar5[7] = uVar83;
  auVar5[8] = uVar84;
  auVar5[9] = uVar85;
  auVar5[10] = uVar86;
  auVar5[0xb] = uVar87;
  auVar5[0xc] = uVar88;
  auVar5[0xd] = uVar89;
  auVar5[0xe] = uVar90;
  auVar5[0xf] = uVar91;
  uVar6 = a64_TBL(ZEXT816(0),auVar5,DAT_7100f46648);
  uVar7 = a64_TBL(ZEXT816(0),auVar51,DAT_7100f46628);
  fVar99 = (fVar47 * (float)uVar65 + fVar48 * (float)uVar93 * (float)uVar96 +
           fVar48 * (float)uVar12 * (float)uVar94) - (float)uVar95 * (float)uVar49;
  fVar100 = (fVar59 * fVar70 + fVar62 * fVar60 * (float)((ulong)uVar96 >> 0x20) +
            fVar62 * fVar102 * (float)((ulong)uVar94 >> 0x20)) -
            fVar78 * (float)((ulong)uVar49 >> 0x20);
  fVar101 = (fVar61 * (float)uVar65 + fVar63 * (float)uVar95 * (float)uVar97 +
            fVar63 * (float)uVar93 * (float)uVar98) - (float)uVar12 * (float)uVar6;
  fVar102 = (fVar64 * fVar70 + fVar79 * fVar78 * (float)((ulong)uVar97 >> 0x20) +
            fVar79 * fVar60 * (float)((ulong)uVar98 >> 0x20)) -
            fVar102 * (float)((ulong)uVar6 >> 0x20);
  uVar6 = a64_TBL(ZEXT816(0),auVar51,DAT_7100f46630);
  fVar70 = (float)((ulong)uVar6 >> 0x20);
  uVar95 = a64_TBL(ZEXT816(0),auVar51,DAT_7100f465a8);
  auVar13._4_4_ = fVar100;
  auVar13._0_4_ = fVar99;
  auVar13._8_4_ = fVar101;
  auVar13._12_4_ = fVar102;
  uVar94 = a64_TBL(ZEXT816(0),auVar13,DAT_7100f46628);
  auVar14._4_4_ = fVar100;
  auVar14._0_4_ = fVar99;
  auVar14._8_4_ = fVar101;
  auVar14._12_4_ = fVar102;
  uVar97 = a64_TBL(ZEXT816(0),auVar14,DAT_7100f46638);
  fVar78 = (float)((ulong)uVar95 >> 0x20);
  uVar96 = a64_TBL(ZEXT816(0),auVar51,DAT_7100f46598);
  fVar47 = (float)((ulong)uVar7 >> 0x20);
  auVar15._4_4_ = fVar100;
  auVar15._0_4_ = fVar99;
  auVar15._8_4_ = fVar101;
  auVar15._12_4_ = fVar102;
  uVar65 = a64_TBL(ZEXT816(0),auVar15,DAT_7100f465a8);
  auVar16._4_4_ = fVar100;
  auVar16._0_4_ = fVar99;
  auVar16._8_4_ = fVar101;
  auVar16._12_4_ = fVar102;
  uVar12 = a64_TBL(ZEXT816(0),auVar16,DAT_7100f46640);
  auVar17._4_4_ = fVar100;
  auVar17._0_4_ = fVar99;
  auVar17._8_4_ = fVar101;
  auVar17._12_4_ = fVar102;
  uVar49 = a64_TBL(ZEXT816(0),auVar17,DAT_7100f46648);
  fVar60 = (float)((ulong)uVar96 >> 0x20);
  auVar18._4_4_ = fVar100;
  auVar18._0_4_ = fVar99;
  auVar18._8_4_ = fVar101;
  auVar18._12_4_ = fVar102;
  uVar93 = a64_TBL(ZEXT816(0),auVar18,DAT_7100f46598);
  fVar59 = ((float)uVar7 * fVar99 + fVar48 * (float)uVar6 * (float)uVar94 +
           fVar48 * (float)uVar96 * (float)uVar65) - (float)uVar95 * (float)uVar93;
  fVar61 = (fVar47 * fVar100 + fVar62 * fVar70 * (float)((ulong)uVar94 >> 0x20) +
           fVar62 * fVar60 * (float)((ulong)uVar65 >> 0x20)) -
           fVar78 * (float)((ulong)uVar93 >> 0x20);
  fVar64 = ((float)uVar7 * fVar101 + fVar63 * (float)uVar95 * (float)uVar97 +
           fVar63 * (float)uVar6 * (float)uVar12) - (float)uVar96 * (float)uVar49;
  fVar47 = (fVar47 * fVar102 + fVar79 * fVar78 * (float)((ulong)uVar97 >> 0x20) +
           fVar79 * fVar70 * (float)((ulong)uVar12 >> 0x20)) -
           fVar60 * (float)((ulong)uVar49 >> 0x20);
  do {
    uVar36 = uVar28 ^ uVar33;
    iVar32 = (int)uVar33;
    iVar23 = (int)uVar28;
    uVar33 = uVar36 >> 0x1b | uVar36 << 0x25;
    uVar28 = uVar36 ^ (uVar28 >> 0x28 | uVar28 << 0x18) ^ uVar36 << 0x10;
    uVar24 = iVar23 + iVar32 & 0x1ff;
  } while (300 < uVar24);
  *(ulong *)(param_1 + 0x80) = uVar28;
  *(ulong *)(param_1 + 0x88) = uVar33;
  fVar59 = (float)CONCAT13((byte)((uint)fVar59 >> 0x18) & (byte)((ulong)_DAT_7100ef9200 >> 0x18),
                           CONCAT12((byte)((uint)fVar59 >> 0x10) &
                                    (byte)((ulong)_DAT_7100ef9200 >> 0x10),
                                    CONCAT11((byte)((uint)fVar59 >> 8) &
                                             (byte)((ulong)_DAT_7100ef9200 >> 8),
                                             SUB41(fVar59,0) & (byte)_DAT_7100ef9200)));
  auVar50._0_8_ =
       CONCAT17((byte)((uint)fVar61 >> 0x18) & (byte)((ulong)_DAT_7100ef9200 >> 0x38),
                CONCAT16((byte)((uint)fVar61 >> 0x10) & (byte)((ulong)_DAT_7100ef9200 >> 0x30),
                         CONCAT15((byte)((uint)fVar61 >> 8) & (byte)((ulong)_DAT_7100ef9200 >> 0x28)
                                  ,CONCAT14(SUB41(fVar61,0) & (byte)((ulong)_DAT_7100ef9200 >> 0x20)
                                            ,fVar59))));
  auVar50[8] = SUB41(fVar64,0) & (byte)_UNK_7100ef9208;
  auVar50[9] = (byte)((uint)fVar64 >> 8) & (byte)((ulong)_UNK_7100ef9208 >> 8);
  auVar50[10] = (byte)((uint)fVar64 >> 0x10) & (byte)((ulong)_UNK_7100ef9208 >> 0x10);
  auVar50[0xb] = (byte)((uint)fVar64 >> 0x18) & (byte)((ulong)_UNK_7100ef9208 >> 0x18);
  auVar52[0xc] = SUB41(fVar47,0) & (byte)((ulong)_UNK_7100ef9208 >> 0x20);
  auVar52._0_12_ = auVar50;
  auVar52[0xd] = (byte)((uint)fVar47 >> 8) & (byte)((ulong)_UNK_7100ef9208 >> 0x28);
  auVar52[0xe] = (byte)((uint)fVar47 >> 0x10) & (byte)((ulong)_UNK_7100ef9208 >> 0x30);
  auVar52[0xf] = (byte)((uint)fVar47 >> 0x18) & (byte)((ulong)_UNK_7100ef9208 >> 0x38);
  fVar64 = -(float)(uVar24 + 200);
  fVar47 = fVar59 * fVar64 + *(float *)(lVar42 + 0xb0);
  fVar59 = (float)((ulong)auVar50._0_8_ >> 0x20) * fVar64 + *(float *)(lVar42 + 0xb4);
  fVar61 = auVar50._8_4_ * fVar64 + *(float *)(lVar42 + 0xb8);
  fVar64 = auVar52._12_4_ * fVar64 + *(float *)(lVar42 + 0xbc);
  FUN_710024a140(&local_80,1);
  if (plVar40[0x27] != 0) {
    plVar46 = (long *)plVar40[0x26];
    uVar24 = 0;
    do {
      uVar28 = (**(code **)(*(long *)*plVar46 + 0x78))();
      if ((uVar28 & 1) == 0) {
        puVar27 = (undefined8 *)(*plVar46 + 0x50);
        plVar29 = (long *)(**(code **)*puVar27)(puVar27);
        puVar43 = FUN_7100139260();
        for (; plVar29 != (long *)0x0; plVar29 = (long *)*plVar29) {
          if (plVar29 == puVar43) {
            if (puVar27 != (undefined8 *)&DAT_00000050) {
              uVar24 = uVar24 + 1;
            }
            break;
          }
        }
      }
      fVar70 = DAT_7100f47074;
      plVar29 = (long *)plVar40[0x26];
      plVar46 = plVar46 + 1;
    } while (plVar29 + plVar40[0x27] != plVar46);
    if (3 < uVar24) goto joined_r0x007100301bb0;
    if (plVar40[0x27] != 0) {
      do {
        do {
          lVar44 = *plVar29;
          puVar27 = (undefined8 *)(lVar44 + 0x50);
          plVar26 = (long *)(**(code **)*puVar27)(puVar27);
          puVar43 = FUN_7100139260();
          for (; plVar26 != (long *)0x0; plVar26 = (long *)*plVar26) {
            if (plVar26 == puVar43) {
              if (puVar27 != (undefined8 *)&DAT_00000050) {
                fVar48 = *(float *)(lVar44 + 0xb0) - fVar47;
                fVar60 = *(float *)(lVar44 + 0xb4) - fVar59;
                fVar62 = *(float *)(lVar44 + 0xb8) - fVar61;
                fVar63 = *(float *)(lVar44 + 0xbc) - fVar64;
                auVar53._0_4_ = fVar48 * fVar48;
                auVar53._4_4_ = fVar60 * fVar60;
                auVar53._8_4_ = fVar62 * fVar62;
                auVar53._12_4_ = fVar63 * fVar63;
                auVar68 = NEON_ext(auVar53,auVar53,8,1);
                fVar48 = auVar68._0_4_ + auVar53._0_4_;
                fVar62 = auVar68._4_4_ + auVar53._4_4_;
                fVar60 = fVar48 + fVar62;
                fVar48 = fVar48 + fVar62;
                auVar54._8_8_ = CONCAT44(fVar48,fVar60);
                auVar54._0_8_ = CONCAT44(fVar48,fVar60);
                auVar68 = NEON_frsqrte(auVar54,4);
                auVar71._0_4_ = auVar68._0_4_ * fVar60;
                auVar71._4_4_ = auVar68._4_4_ * fVar48;
                auVar71._8_4_ = auVar68._8_4_ * fVar60;
                auVar71._12_4_ = auVar68._12_4_ * fVar48;
                auVar76 = NEON_frsqrts(auVar68,auVar71,4);
                auVar66._0_4_ = auVar68._0_4_ * auVar76._0_4_;
                auVar66._4_4_ = auVar68._4_4_ * auVar76._4_4_;
                auVar66._8_4_ = auVar68._8_4_ * auVar76._8_4_;
                auVar66._12_4_ = auVar68._12_4_ * auVar76._12_4_;
                auVar72._0_4_ = fVar60 * auVar66._0_4_;
                auVar72._4_4_ = fVar48 * auVar66._4_4_;
                auVar72._8_4_ = fVar60 * auVar66._8_4_;
                auVar72._12_4_ = fVar48 * auVar66._12_4_;
                auVar68 = NEON_frsqrts(auVar66,auVar72,4);
                fVar48 = 0.0;
                if (fVar60 != 0.0) {
                  fVar48 = fVar60 * auVar66._0_4_ * auVar68._0_4_;
                }
                if (fVar48 < fVar70) goto LAB_7100301530;
              }
              break;
            }
          }
          plVar29 = plVar29 + 1;
        } while (plVar29 != plVar46);
LAB_7100301530:
        plVar26 = (long *)plVar40[0x26];
        lVar44 = plVar40[0x27];
        if (plVar26 + lVar44 != plVar29) {
          uVar28 = (**(code **)(*(long *)*plVar29 + 0x78))();
          if ((uVar28 & 1) == 0) {
            lVar44 = *plVar29;
            if (lVar44 != 0) goto LAB_7100301750;
            plVar26 = (long *)plVar40[0x26];
            lVar44 = plVar40[0x27];
            break;
          }
          plVar26 = (long *)plVar40[0x26];
          lVar44 = plVar40[0x27];
          plVar29 = plVar29 + 1;
        }
        plVar46 = plVar26 + lVar44;
      } while (plVar46 != plVar29);
      if (lVar44 != 0) {
        plVar46 = plVar26 + lVar44;
        do {
          do {
            lVar44 = *plVar26;
            puVar27 = (undefined8 *)(lVar44 + 0x50);
            plVar29 = (long *)(**(code **)*puVar27)(puVar27);
            puVar43 = FUN_7100139cc0();
            for (; plVar29 != (long *)0x0; plVar29 = (long *)*plVar29) {
              if (plVar29 == puVar43) {
                if (puVar27 != (undefined8 *)&DAT_00000050) {
                  fVar48 = *(float *)(lVar44 + 0xb0) - fVar47;
                  fVar60 = *(float *)(lVar44 + 0xb4) - fVar59;
                  fVar62 = *(float *)(lVar44 + 0xb8) - fVar61;
                  fVar63 = *(float *)(lVar44 + 0xbc) - fVar64;
                  auVar55._0_4_ = fVar48 * fVar48;
                  auVar55._4_4_ = fVar60 * fVar60;
                  auVar55._8_4_ = fVar62 * fVar62;
                  auVar55._12_4_ = fVar63 * fVar63;
                  auVar68 = NEON_ext(auVar55,auVar55,8,1);
                  fVar48 = auVar68._0_4_ + auVar55._0_4_;
                  fVar62 = auVar68._4_4_ + auVar55._4_4_;
                  fVar60 = fVar48 + fVar62;
                  fVar48 = fVar48 + fVar62;
                  auVar56._8_8_ = CONCAT44(fVar48,fVar60);
                  auVar56._0_8_ = CONCAT44(fVar48,fVar60);
                  auVar68 = NEON_frsqrte(auVar56,4);
                  auVar73._0_4_ = auVar68._0_4_ * fVar60;
                  auVar73._4_4_ = auVar68._4_4_ * fVar48;
                  auVar73._8_4_ = auVar68._8_4_ * fVar60;
                  auVar73._12_4_ = auVar68._12_4_ * fVar48;
                  auVar76 = NEON_frsqrts(auVar68,auVar73,4);
                  auVar67._0_4_ = auVar68._0_4_ * auVar76._0_4_;
                  auVar67._4_4_ = auVar68._4_4_ * auVar76._4_4_;
                  auVar67._8_4_ = auVar68._8_4_ * auVar76._8_4_;
                  auVar67._12_4_ = auVar68._12_4_ * auVar76._12_4_;
                  auVar74._0_4_ = fVar60 * auVar67._0_4_;
                  auVar74._4_4_ = fVar48 * auVar67._4_4_;
                  auVar74._8_4_ = fVar60 * auVar67._8_4_;
                  auVar74._12_4_ = fVar48 * auVar67._12_4_;
                  auVar68 = NEON_frsqrts(auVar67,auVar74,4);
                  fVar48 = 0.0;
                  if (fVar60 != 0.0) {
                    fVar48 = fVar60 * auVar67._0_4_ * auVar68._0_4_;
                  }
                  if (fVar48 < fVar70) goto LAB_7100301614;
                }
                break;
              }
            }
            plVar26 = plVar26 + 1;
          } while (plVar26 != plVar46);
LAB_7100301614:
          plVar29 = (long *)plVar40[0x26];
          lVar44 = plVar40[0x27];
          if (plVar29 + lVar44 != plVar26) {
            uVar28 = (**(code **)(*(long *)*plVar26 + 0x78))();
            if ((uVar28 & 1) == 0) {
              lVar44 = *plVar26;
              if (lVar44 != 0) goto LAB_7100301750;
              plVar29 = (long *)plVar40[0x26];
              lVar44 = plVar40[0x27];
              break;
            }
            plVar29 = (long *)plVar40[0x26];
            lVar44 = plVar40[0x27];
            plVar26 = plVar26 + 1;
          }
          plVar46 = plVar29 + lVar44;
        } while (plVar46 != plVar26);
        if (lVar44 != 0) {
          plVar46 = plVar29 + lVar44;
          do {
            do {
              lVar44 = *plVar29;
              puVar27 = (undefined8 *)(lVar44 + 0x50);
              plVar26 = (long *)(**(code **)*puVar27)(puVar27);
              puVar43 = FUN_7100229fa0();
              for (; plVar26 != (long *)0x0; plVar26 = (long *)*plVar26) {
                if (plVar26 == puVar43) {
                  if (puVar27 != (undefined8 *)&DAT_00000050) {
                    fVar48 = *(float *)(lVar44 + 0xb0) - fVar47;
                    fVar60 = *(float *)(lVar44 + 0xb4) - fVar59;
                    fVar62 = *(float *)(lVar44 + 0xb8) - fVar61;
                    fVar63 = *(float *)(lVar44 + 0xbc) - fVar64;
                    auVar57._0_4_ = fVar48 * fVar48;
                    auVar57._4_4_ = fVar60 * fVar60;
                    auVar57._8_4_ = fVar62 * fVar62;
                    auVar57._12_4_ = fVar63 * fVar63;
                    auVar68 = NEON_ext(auVar57,auVar57,8,1);
                    fVar48 = auVar68._0_4_ + auVar57._0_4_;
                    fVar62 = auVar68._4_4_ + auVar57._4_4_;
                    fVar60 = fVar48 + fVar62;
                    fVar48 = fVar48 + fVar62;
                    auVar58._8_8_ = CONCAT44(fVar48,fVar60);
                    auVar58._0_8_ = CONCAT44(fVar48,fVar60);
                    auVar68 = NEON_frsqrte(auVar58,4);
                    auVar75._0_4_ = auVar68._0_4_ * fVar60;
                    auVar75._4_4_ = auVar68._4_4_ * fVar48;
                    auVar75._8_4_ = auVar68._8_4_ * fVar60;
                    auVar75._12_4_ = auVar68._12_4_ * fVar48;
                    auVar76 = NEON_frsqrts(auVar68,auVar75,4);
                    auVar69._0_4_ = auVar68._0_4_ * auVar76._0_4_;
                    auVar69._4_4_ = auVar68._4_4_ * auVar76._4_4_;
                    auVar69._8_4_ = auVar68._8_4_ * auVar76._8_4_;
                    auVar69._12_4_ = auVar68._12_4_ * auVar76._12_4_;
                    auVar77._0_4_ = fVar60 * auVar69._0_4_;
                    auVar77._4_4_ = fVar48 * auVar69._4_4_;
                    auVar77._8_4_ = fVar60 * auVar69._8_4_;
                    auVar77._12_4_ = fVar48 * auVar69._12_4_;
                    auVar68 = NEON_frsqrts(auVar69,auVar77,4);
                    fVar48 = 0.0;
                    if (fVar60 != 0.0) {
                      fVar48 = fVar60 * auVar69._0_4_ * auVar68._0_4_;
                    }
                    if (fVar48 < fVar70) goto LAB_71003016f8;
                  }
                  break;
                }
              }
              plVar29 = plVar29 + 1;
            } while (plVar29 != plVar46);
LAB_71003016f8:
            lVar44 = plVar40[0x26];
            lVar37 = plVar40[0x27];
            if ((long *)(lVar44 + lVar37 * 8) != plVar29) {
              uVar28 = (**(code **)(*(long *)*plVar29 + 0x78))();
              if ((uVar28 & 1) == 0) {
                if (*plVar29 != 0) {
                  plVar46 = (long *)(*plVar29 + 0x48);
                  (**(code **)(*plVar46 + 0x10))(plVar46);
                  (**(code **)(*plVar46 + 0x18))(plVar46);
                  goto joined_r0x007100301bb0;
                }
                break;
              }
              lVar44 = plVar40[0x26];
              lVar37 = plVar40[0x27];
              plVar29 = plVar29 + 1;
            }
            plVar46 = (long *)(lVar44 + lVar37 * 8);
          } while (plVar46 != plVar29);
        }
      }
    }
  }
LAB_7100301774:
  puVar30 = *(uint **)(*(long *)(lVar38 + 0xd8) + 0x170);
  piVar1 = (int *)((long)puVar30 + (ulong)*puVar30);
  local_100 = *(long **)(*(long *)PTR_DAT_71015faab8 + 0x248);
  uStack_f8 = 0x1fffffffffffffff;
  local_d0 = (long *)0x0;
  local_b8 = 0;
  local_b0 = 0;
  local_c0 = (long *)0x0;
  plVar46 = (long *)(**(code **)(*local_100 + 0x10))(local_100,0x20,8);
  FUN_7100191740(&local_100,plVar46,4,local_c0 + local_b8,0,(long *)0x0);
  if (((0xe < *(ushort *)((long)piVar1 - (long)*piVar1)) &&
      (uVar28 = (ulong)((ushort *)((long)piVar1 - (long)*piVar1))[7], uVar28 != 0)) &&
     (puVar30 = (uint *)((long)piVar1 + uVar28), puVar30 = (uint *)((long)puVar30 + (ulong)*puVar30)
     , puVar30 != (uint *)0x0)) {
    puVar34 = puVar30 + 1;
    if (*puVar30 != 0) {
      puVar31 = puVar34 + *puVar30;
      puVar45 = puVar34;
      do {
        puVar21 = puVar45 + 1;
        do {
          puVar35 = puVar21;
          uVar28 = (ulong)puVar35[-1];
          lVar44 = uVar28 + *(ushort *)
                             ((long)puVar35 +
                             (uVar28 - (long)*(int *)((long)puVar35 + (uVar28 - 4))));
          lVar44 = lVar44 + (ulong)*(uint *)((long)puVar35 + lVar44 + -4);
          lVar44 = lVar44 + (ulong)*(ushort *)
                                    ((long)puVar35 +
                                    (lVar44 - *(int *)((long)puVar35 + lVar44 + -4)));
          lVar44 = lVar44 + (ulong)*(uint *)((long)puVar35 + lVar44 + -4);
          lVar37 = lVar44 - *(int *)((long)puVar35 + lVar44 + -4);
          if (((8 < *(ushort *)((long)puVar35 + lVar37 + -4)) &&
              (uVar28 = (ulong)*(ushort *)((long)puVar35 + lVar37 + 4), uVar28 != 0)) &&
             (*(long *)((long)puVar35 + lVar44 + uVar28 + -4) == -0x50c7e9428ea162e5)) break;
          puVar21 = puVar35 + 1;
          puVar45 = puVar35;
        } while ((long)(puVar35 + 1) - (long)puVar31 != 4);
        if (puVar31 == puVar45) break;
        uVar24 = *puVar45;
        plVar46 = (long *)plVar40[0xb];
        lVar44 = nn::os::GetTlsValue(*(undefined4 *)PTR_DAT_71015fad18);
        if (0xf < *(ulong *)(lVar44 + 0x80)) {
                    /* WARNING: Subroutine does not return */
          abort();
        }
        *(long **)(lVar44 + *(ulong *)(lVar44 + 0x80) * 8) = plVar46;
        *(long *)(lVar44 + 0x80) = *(long *)(lVar44 + 0x80) + 1;
        puVar43 = (undefined8 *)(**(code **)(*plVar46 + 0x10))(plVar46,0x10d0,0x10);
        if (puVar43 == (undefined8 *)0x0) {
          (**(code **)(*plVar46 + 0x90))(plVar46);
        }
        FUN_71002334d0(puVar43,plVar46,plVar40 + 0xd,(int *)((long)puVar45 + (ulong)uVar24));
        puVar43[1] = plVar46;
        puVar43[2] = puVar43;
        puVar43[3] = 0x10d0;
        puVar43[4] = 0x10;
        *(long *)(lVar44 + 0x80) = *(long *)(lVar44 + 0x80) + -1;
        if (puVar43 == (undefined8 *)0x0) {
          local_78 = (undefined8 *)0x0;
        }
        else {
          plVar46 = puVar43 + 9;
          (**(code **)(*plVar46 + 0x10))(plVar46);
          local_78 = puVar43;
          (**(code **)(*plVar46 + 0x10))(plVar46);
        }
        FUN_7100229810(&local_100,(long *)&local_78);
        if (local_78 != (undefined8 *)0x0) {
          (**(code **)(local_78[9] + 0x18))();
        }
        local_78 = puVar43;
        FUN_7100229810(plVar40 + 0x1e,(long *)&local_78);
        if (local_78 != (undefined8 *)0x0) {
          (**(code **)(local_78[9] + 0x18))();
          local_78 = (undefined8 *)0x0;
        }
        puVar31 = puVar34 + *puVar30;
        puVar45 = puVar45 + 1;
      } while (puVar45 != puVar31);
    }
  }
  if (local_b8 != 0) {
    lVar44 = *local_c0;
    plVar46 = (long *)(*(code *)**(undefined8 **)(lVar44 + 0x50))((undefined8 *)(lVar44 + 0x50));
    if (((*PTR_DAT_71015fcbb8 & 1) == 0) &&
       (iVar23 = __cxa_guard_acquire(PTR_DAT_71015fcbb8), iVar23 != 0)) {
      puVar43 = FUN_7100139260();
      *(undefined8 **)PTR_DAT_71015fcbc0 = puVar43;
      __cxa_guard_release(PTR_DAT_71015fcbb8);
    }
    for (; plVar46 != (long *)PTR_DAT_71015fcbc0; plVar46 = (long *)*plVar46) {
    }
    *(undefined1 *)(lVar44 + 0xc0) = 1;
    *(undefined4 *)(lVar44 + 0xf0c) = 1;
    *(undefined4 *)(lVar44 + 0xf14) = 2;
    *(long *)(lVar44 + 0xa8) = auVar51._8_8_;
    *(long *)(lVar44 + 0xa0) = auVar51._0_8_;
    auVar51._8_4_ = fVar61;
    auVar51._0_8_ = CONCAT44(fVar59,fVar47);
    auVar51._12_4_ = fVar64;
    *(undefined4 *)(lVar44 + 0xf30) = 3;
    *(long *)(lVar44 + 0xb8) = auVar51._8_8_;
    *(ulong *)(lVar44 + 0xb0) = CONCAT44(fVar59,fVar47);
    (**(code **)(*plVar40 + 0x50))(plVar40,1);
    if (local_b8 != 0) {
      lVar44 = local_b8;
      plVar46 = local_c0;
      do {
        lVar44 = lVar44 + -1;
        if (*plVar46 != 0) {
          (**(code **)(*(long *)(*plVar46 + 0x48) + 0x18))();
          *plVar46 = 0;
        }
        plVar46 = plVar46 + 1;
      } while (lVar44 != 0);
    }
  }
  if (local_b0 != 0) {
    (**(code **)(*local_100 + 0x18))(local_100,local_c0,local_b0 << 3,8);
  }
  if (alStack_f0 == local_d0) {
    (**(code **)(*local_d0 + 0x20))();
  }
  else if (local_d0 != (long *)0x0) {
    (**(code **)(*local_d0 + 0x28))();
  }
joined_r0x007100301bb0:
  if (lVar42 != 0) {
    (**(code **)(*(long *)(lVar42 + 0x48) + 0x18))((long *)(lVar42 + 0x48));
  }
  if (lVar41 != 0) {
    (**(code **)(*(long *)(lVar41 + 0x48) + 0x18))((long *)(lVar41 + 0x48));
  }
  if (plVar40 != (long *)0x0) {
    (**(code **)(plVar40[9] + 0x18))(plVar40 + 9);
  }
  if (lVar39 != 0) {
    (**(code **)(*(long *)(lVar39 + 0x48) + 0x18))((long *)(lVar39 + 0x48));
  }
  if (lVar38 != 0) {
    (**(code **)(*(long *)(lVar38 + 0x48) + 0x18))((long *)(lVar38 + 0x48));
  }
  return 0;
LAB_7100301750:
  (**(code **)(*(long *)(lVar44 + 0x48) + 0x10))();
  (**(code **)(*(long *)(lVar44 + 0x48) + 0x18))();
  if (lVar44 != 0) goto joined_r0x007100301bb0;
  goto LAB_7100301774;
}

