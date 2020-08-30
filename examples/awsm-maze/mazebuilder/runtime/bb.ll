; ModuleID = 'runtime/bb.bc'
source_filename = "runtime/bb.c"
target datalayout = "e-m:e-p:32:32-Fi8-i64:64-v128:64:128-a:0:32-n32-S64"
target triple = "thumbv7em-v7m-none-gnueabi"

%struct._reent = type { i32, %struct.__sFILE*, %struct.__sFILE*, %struct.__sFILE*, i32, [25 x i8], i32, %struct.__locale_t*, i32, void (%struct._reent*)*, %struct._Bigint*, i32, %struct._Bigint*, %struct._Bigint**, i32, i8*, %union.anon.0, %struct._atexit*, %struct._atexit, void (i32)**, %struct._glue, [3 x %struct.__sFILE] }
%struct.__sFILE = type { i8*, i32, i32, i16, i16, %struct.__sbuf, i32, i8*, i32 (%struct._reent*, i8*, i8*, i32)*, i32 (%struct._reent*, i8*, i8*, i32)*, i32 (%struct._reent*, i8*, i32, i32)*, i32 (%struct._reent*, i8*)*, %struct.__sbuf, i8*, i32, [3 x i8], [1 x i8], %struct.__sbuf, i32, i32, %struct._reent*, %struct.__lock*, %struct._mbstate_t, i32 }
%struct.__sbuf = type { i8*, i32 }
%struct.__lock = type opaque
%struct._mbstate_t = type { i32, %union.anon }
%union.anon = type { i32 }
%struct.__locale_t = type opaque
%struct._Bigint = type { %struct._Bigint*, i32, i32, i32, i32, [1 x i32] }
%union.anon.0 = type { %struct.anon, [32 x i8] }
%struct.anon = type { i32, i8*, [26 x i8], %struct.__tm, i32, i64, %struct._rand48, %struct._mbstate_t, %struct._mbstate_t, %struct._mbstate_t, [8 x i8], [24 x i8], i32, %struct._mbstate_t, %struct._mbstate_t, %struct._mbstate_t, %struct._mbstate_t, %struct._mbstate_t, i32 }
%struct.__tm = type { i32, i32, i32, i32, i32, i32, i32, i32, i32 }
%struct._rand48 = type { [3 x i16], [3 x i16], i16 }
%struct._atexit = type { %struct._atexit*, i32, [32 x void ()*], %struct._on_exit_args }
%struct._on_exit_args = type { [32 x i8*], [32 x i8*], i32, i32 }
%struct._glue = type { %struct._glue*, i32, %struct.__sFILE* }
%struct.table_entry = type { i32, i8* }
%struct.__va_list = type { i8* }

@__heap_brk = internal unnamed_addr global i8* null, align 4, !dbg !0
@__heap_start = external dso_local global i8, align 1
@__heap_end = external dso_local global i8, align 1
@.str = private unnamed_addr constant [30 x i8] c"%s:%d: assertion \22%s\22 failed\0A\00", align 1
@.str.1 = private unnamed_addr constant [2 x i8] c"%\00", align 1
@.str.2 = private unnamed_addr constant [2 x i8] c"-\00", align 1
@_impure_ptr = external dso_local local_unnamed_addr global %struct._reent*, align 4
@__memory = external dso_local global [0 x i8], align 1
@memory_size = dso_local local_unnamed_addr constant i32 65536, align 4, !dbg !61
@__table = external dso_local global [0 x %struct.table_entry], align 4
@__memory_start = external dso_local global i8, align 1
@__box_datasp = dso_local local_unnamed_addr global i8* @__memory_start, align 4, !dbg !64
@__memory_end = external dso_local global i8, align 1
@__data_init_start = external dso_local local_unnamed_addr global i32, align 4
@__data_start = external dso_local global i32, align 4
@__data_end = external dso_local global i32, align 4
@__bss_start = external dso_local global i32, align 4
@__bss_end = external dso_local global i32, align 4
@__box_importjumptable = dso_local local_unnamed_addr global i32* null, align 4, !dbg !71
@__box_exportjumptable = dso_local constant [4 x i32] [i32 ptrtoint (i32 (i32*)* @__box_init to i32), i32 ptrtoint (i8* (i32)* @__box_push to i32), i32 ptrtoint (void (i32)* @__box_pop to i32), i32 ptrtoint (i32 (i32, i32, i32)* @wasmf_mandlebrot to i32)], section ".jumptable", align 4, !dbg !66
@llvm.used = appending global [8 x i8*] [i8* bitcast ([4 x i32]* @__box_exportjumptable to i8*), i8* bitcast (void ()* @__wrap_abort to i8*), i8* bitcast (void (i32)* @__wrap_exit to i8*), i8* bitcast (i32 (%struct.__sFILE*)* @__wrap_fflush to i8*), i8* bitcast (i32 (%struct.__sFILE*, i8*, ...)* @__wrap_fprintf to i8*), i8* bitcast (i32 (i8*, ...)* @__wrap_printf to i8*), i8* bitcast (i32 (%struct.__sFILE*, i8*, [1 x i32])* @__wrap_vfprintf to i8*), i8* bitcast (i32 (i8*, [1 x i32])* @__wrap_vprintf to i8*)], section "llvm.metadata"

@printf_ = dso_local alias i32 (i8*, ...), i32 (i8*, ...)* @__wrap_printf
@abort_ = dso_local alias void (), void ()* @__wrap_abort
@__box_abort = dso_local alias void (i32), void (i32)* @env___box_abort
@__box_write = dso_local alias i32 (i32, i8*, i32), bitcast (i32 (i32, i32, i32)* @env___box_write to i32 (i32, i8*, i32)*)
@__box_flush = dso_local alias i32 (i32), i32 (i32)* @env___box_flush

; Function Attrs: minsize nofree norecurse nounwind optsize
define dso_local i8* @_sbrk(i32) local_unnamed_addr #0 !dbg !81 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !86, metadata !DIExpression()), !dbg !88
  %2 = load i8*, i8** @__heap_brk, align 4, !dbg !89, !tbaa !91
  %3 = icmp eq i8* %2, null, !dbg !89
  %4 = select i1 %3, i8* @__heap_start, i8* %2, !dbg !95
  call void @llvm.dbg.value(metadata i8* %4, metadata !87, metadata !DIExpression()), !dbg !88
  %5 = getelementptr inbounds i8, i8* %4, i32 %0, !dbg !96
  %6 = icmp ugt i8* %5, @__heap_end, !dbg !98
  %7 = select i1 %6, i8* inttoptr (i32 -1 to i8*), i8* %4, !dbg !99
  %8 = xor i1 %6, true, !dbg !100
  %9 = or i1 %3, %8, !dbg !100
  br i1 %9, label %10, label %12, !dbg !100

10:                                               ; preds = %1
  %11 = select i1 %6, i8* %4, i8* %5, !dbg !99
  store i8* %11, i8** @__heap_brk, align 4, !dbg !100, !tbaa !91
  br label %12, !dbg !100

12:                                               ; preds = %10, %1
  ret i8* %7, !dbg !100
}

; Function Attrs: argmemonly nounwind
declare void @llvm.lifetime.start.p0i8(i64 immarg, i8* nocapture) #1

; Function Attrs: argmemonly nounwind
declare void @llvm.lifetime.end.p0i8(i64 immarg, i8* nocapture) #1

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @__wrap_abort() #2 !dbg !101 {
  call void @llvm.dbg.value(metadata i32 -1, metadata !104, metadata !DIExpression()) #5, !dbg !109
  %1 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !111, !tbaa !91
  %2 = load void (i32)*, void (i32)** %1, align 4, !dbg !111, !tbaa !112
  tail call void %2(i32 -1) #11, !dbg !114
  unreachable, !dbg !115
}

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @__wrap_exit(i32) #2 !dbg !116 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !118, metadata !DIExpression()), !dbg !119
  %2 = icmp slt i32 %0, 0, !dbg !120
  %3 = sub nsw i32 0, %0, !dbg !121
  %4 = select i1 %2, i32 %0, i32 %3, !dbg !121
  call void @llvm.dbg.value(metadata i32 %4, metadata !104, metadata !DIExpression()) #5, !dbg !122
  %5 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !124, !tbaa !91
  %6 = load void (i32)*, void (i32)** %5, align 4, !dbg !124, !tbaa !112
  tail call void %6(i32 %4) #11, !dbg !125
  unreachable, !dbg !126
}

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @__assert_func(i8*, i32, i8* nocapture readnone, i8*) local_unnamed_addr #2 !dbg !127 {
  call void @llvm.dbg.value(metadata i8* %0, metadata !131, metadata !DIExpression()), !dbg !135
  call void @llvm.dbg.value(metadata i32 %1, metadata !132, metadata !DIExpression()), !dbg !135
  call void @llvm.dbg.value(metadata i8* %2, metadata !133, metadata !DIExpression()), !dbg !135
  call void @llvm.dbg.value(metadata i8* %3, metadata !134, metadata !DIExpression()), !dbg !135
  %5 = tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([30 x i8], [30 x i8]* @.str, i32 0, i32 0), i8* %0, i32 %1, i8* %3) #11, !dbg !136
  call void @llvm.dbg.value(metadata i32 -1, metadata !104, metadata !DIExpression()) #5, !dbg !137
  %6 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !139, !tbaa !91
  %7 = load void (i32)*, void (i32)** %6, align 4, !dbg !139, !tbaa !112
  tail call void %7(i32 -1) #11, !dbg !140
  unreachable, !dbg !141
}

; Function Attrs: minsize optsize
declare dso_local i32 @printf(i8*, ...) local_unnamed_addr #3

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @_exit(i32) local_unnamed_addr #2 !dbg !142 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !144, metadata !DIExpression()), !dbg !145
  %2 = icmp slt i32 %0, 0, !dbg !146
  %3 = sub nsw i32 0, %0, !dbg !147
  %4 = select i1 %2, i32 %0, i32 %3, !dbg !147
  call void @llvm.dbg.value(metadata i32 %4, metadata !104, metadata !DIExpression()) #5, !dbg !148
  %5 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !150, !tbaa !91
  %6 = load void (i32)*, void (i32)** %5, align 4, !dbg !150, !tbaa !112
  tail call void %6(i32 %4) #11, !dbg !151
  unreachable, !dbg !152
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__box_cbprintf(i32 (i8*, i8*, i32)* nocapture, i8*, i8*, [1 x i32]) local_unnamed_addr #4 !dbg !153 {
  %5 = alloca i32, align 4
  %6 = alloca i8, align 1
  %7 = alloca i8, align 1
  %8 = alloca i8, align 1
  %9 = alloca i8, align 1
  %10 = extractvalue [1 x i32] %3, 0
  call void @llvm.dbg.value(metadata i32 %10, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 (i8*, i8*, i32)* %0, metadata !166, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %1, metadata !167, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %2, metadata !168, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %2, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 0, metadata !171, metadata !DIExpression()), !dbg !257
  %11 = bitcast i32* %5 to i8*, !dbg !258
  %12 = bitcast i32* %5 to i8**, !dbg !259
  br label %13, !dbg !260

13:                                               ; preds = %303, %4
  %14 = phi i32 [ 0, %4 ], [ %304, %303 ], !dbg !261
  %15 = phi i8* [ %2, %4 ], [ %185, %303 ], !dbg !257
  %16 = phi i32 [ %10, %4 ], [ %184, %303 ]
  %17 = phi i32 [ undef, %4 ], [ %305, %303 ]
  call void @llvm.dbg.value(metadata i32 %16, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %15, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %14, metadata !171, metadata !DIExpression()), !dbg !257
  %18 = call i32 @strcspn(i8* %15, i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str.1, i32 0, i32 0)) #11, !dbg !262
  call void @llvm.dbg.value(metadata i32 %18, metadata !172, metadata !DIExpression()), !dbg !258
  %19 = icmp eq i32 %18, 0, !dbg !263
  br i1 %19, label %27, label %20, !dbg !264

20:                                               ; preds = %13
  %21 = call i32 %0(i8* %1, i8* %15, i32 %18) #11, !dbg !265
  call void @llvm.dbg.value(metadata i32 %21, metadata !174, metadata !DIExpression()), !dbg !266
  %22 = icmp slt i32 %21, 0, !dbg !267
  %23 = select i1 %22, i32 0, i32 %21, !dbg !269
  %24 = add nsw i32 %23, %14, !dbg !269
  %25 = select i1 %22, i32 %21, i32 %17, !dbg !269
  call void @llvm.dbg.value(metadata i32 %24, metadata !171, metadata !DIExpression()), !dbg !257
  %26 = icmp sgt i32 %21, -1
  br i1 %26, label %27, label %306

27:                                               ; preds = %20, %13
  %28 = phi i32 [ %24, %20 ], [ %14, %13 ], !dbg !261
  %29 = phi i32 [ %25, %20 ], [ %17, %13 ]
  call void @llvm.dbg.value(metadata i32 %28, metadata !171, metadata !DIExpression()), !dbg !257
  %30 = getelementptr inbounds i8, i8* %15, i32 %18, !dbg !270
  call void @llvm.dbg.value(metadata i8* %30, metadata !170, metadata !DIExpression()), !dbg !257
  %31 = load i8, i8* %30, align 1, !dbg !271, !tbaa !273
  %32 = icmp eq i8 %31, 0, !dbg !271
  br i1 %32, label %306, label %33, !dbg !274

33:                                               ; preds = %27
  call void @llvm.dbg.value(metadata i8 0, metadata !177, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 0, metadata !179, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 0, metadata !180, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 0, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 0, metadata !182, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 99, metadata !183, metadata !DIExpression()), !dbg !258
  call void @llvm.lifetime.start.p0i8(i64 4, i8* nonnull %11) #5, !dbg !275
  call void @llvm.dbg.value(metadata i32 0, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 0, i32* %5, align 4, !dbg !276, !tbaa !112
  call void @llvm.dbg.value(metadata i32 0, metadata !185, metadata !DIExpression()), !dbg !258
  br label %34, !dbg !277

34:                                               ; preds = %88, %33
  %35 = phi i32 [ 0, %33 ], [ %94, %88 ]
  %36 = phi i32 [ 0, %33 ], [ %95, %88 ]
  %37 = phi i1 [ false, %33 ], [ %61, %88 ]
  %38 = phi i1 [ false, %33 ], [ %65, %88 ]
  %39 = phi i1 [ false, %33 ], [ %53, %88 ]
  %40 = phi i8* [ %30, %33 ], [ %69, %88 ]
  %41 = phi i32 [ %16, %33 ], [ %91, %88 ]
  br label %42, !dbg !278

42:                                               ; preds = %75, %34
  %43 = phi i32 [ %78, %75 ], [ %35, %34 ]
  %44 = phi i32 [ %56, %75 ], [ %36, %34 ]
  %45 = phi i1 [ true, %75 ], [ %37, %34 ]
  %46 = phi i1 [ %65, %75 ], [ %38, %34 ]
  %47 = phi i1 [ %53, %75 ], [ %39, %34 ]
  %48 = phi i8* [ %69, %75 ], [ %40, %34 ]
  br label %49, !dbg !278

49:                                               ; preds = %79, %42
  %50 = phi i32 [ %44, %42 ], [ 0, %79 ]
  %51 = phi i1 [ %45, %42 ], [ false, %79 ]
  %52 = phi i1 [ %46, %42 ], [ %65, %79 ]
  %53 = phi i1 [ %47, %42 ], [ true, %79 ]
  %54 = phi i8* [ %48, %42 ], [ %69, %79 ]
  br label %55, !dbg !278

55:                                               ; preds = %83, %49
  %56 = phi i32 [ %86, %83 ], [ %50, %49 ]
  %57 = phi i1 [ false, %83 ], [ %51, %49 ]
  %58 = phi i1 [ %65, %83 ], [ %52, %49 ]
  %59 = phi i8* [ %69, %83 ], [ %54, %49 ]
  br label %60, !dbg !278

60:                                               ; preds = %87, %55
  %61 = phi i1 [ %57, %55 ], [ true, %87 ]
  %62 = phi i1 [ %58, %55 ], [ %65, %87 ]
  %63 = phi i8* [ %59, %55 ], [ %69, %87 ]
  br label %64, !dbg !278

64:                                               ; preds = %87, %60
  %65 = phi i1 [ %62, %60 ], [ true, %87 ]
  %66 = phi i8* [ %63, %60 ], [ %69, %87 ]
  br label %67, !dbg !278

67:                                               ; preds = %154, %64
  %68 = phi i8* [ %69, %154 ], [ %66, %64 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 undef, metadata !177, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 undef, metadata !179, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 undef, metadata !180, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %43, metadata !182, metadata !DIExpression()), !dbg !258
  %69 = getelementptr inbounds i8, i8* %68, i32 1, !dbg !279
  %70 = load i8, i8* %69, align 1, !dbg !279, !tbaa !273
  %71 = add i8 %70, -48, !dbg !280
  %72 = icmp ult i8 %71, 10, !dbg !280
  br i1 %72, label %73, label %87, !dbg !280

73:                                               ; preds = %67
  %74 = zext i8 %70 to i32, !dbg !279
  br i1 %61, label %75, label %79, !dbg !281

75:                                               ; preds = %73
  %76 = mul i32 %43, 10, !dbg !283
  %77 = add nsw i32 %74, -48, !dbg !286
  %78 = add i32 %77, %76, !dbg !287
  call void @llvm.dbg.value(metadata i32 %78, metadata !182, metadata !DIExpression()), !dbg !258
  br label %42, !dbg !288, !llvm.loop !289

79:                                               ; preds = %73
  %80 = icmp ugt i8 %70, 48, !dbg !291
  %81 = icmp ne i32 %56, 0, !dbg !293
  %82 = or i1 %81, %80, !dbg !294
  br i1 %82, label %83, label %49, !dbg !294, !llvm.loop !289

83:                                               ; preds = %79
  %84 = mul i32 %56, 10, !dbg !295
  %85 = add nsw i32 %74, -48, !dbg !297
  %86 = add i32 %85, %84, !dbg !298
  call void @llvm.dbg.value(metadata i32 %86, metadata !181, metadata !DIExpression()), !dbg !258
  br label %55, !dbg !299, !llvm.loop !289

87:                                               ; preds = %67
  switch i8 %70, label %154 [
    i8 42, label %88
    i8 46, label %60
    i8 45, label %64
    i8 37, label %96
    i8 99, label %97
    i8 115, label %103
    i8 100, label %118
    i8 105, label %118
    i8 117, label %138
  ], !dbg !300, !llvm.loop !289

88:                                               ; preds = %87
  %89 = inttoptr i32 %41 to i8*, !dbg !301
  %90 = getelementptr inbounds i8, i8* %89, i32 4, !dbg !301
  %91 = ptrtoint i8* %90 to i32, !dbg !301
  call void @llvm.dbg.value(metadata i32 %91, metadata !169, metadata !DIExpression()), !dbg !257
  %92 = inttoptr i32 %41 to i32*, !dbg !301
  %93 = load i32, i32* %92, align 4, !dbg !301
  %94 = select i1 %61, i32 %93, i32 %43
  %95 = select i1 %61, i32 %56, i32 %93
  br label %34, !llvm.loop !289

96:                                               ; preds = %87
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 99, metadata !183, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 37, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 37, i32* %5, align 4, !dbg !304, !tbaa !112
  call void @llvm.dbg.value(metadata i32 1, metadata !185, metadata !DIExpression()), !dbg !258
  br label %179, !dbg !306

97:                                               ; preds = %87
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 99, metadata !183, metadata !DIExpression()), !dbg !258
  %98 = inttoptr i32 %41 to i8*, !dbg !307
  %99 = getelementptr inbounds i8, i8* %98, i32 4, !dbg !307
  %100 = ptrtoint i8* %99 to i32, !dbg !307
  call void @llvm.dbg.value(metadata i32 %100, metadata !169, metadata !DIExpression()), !dbg !257
  %101 = inttoptr i32 %41 to i32*, !dbg !307
  %102 = load i32, i32* %101, align 4, !dbg !307
  call void @llvm.dbg.value(metadata i32 %102, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %102, i32* %5, align 4, !dbg !309, !tbaa !112
  call void @llvm.dbg.value(metadata i32 1, metadata !185, metadata !DIExpression()), !dbg !258
  br label %179, !dbg !310

103:                                              ; preds = %87
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %43, metadata !182, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %43, metadata !182, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %43, metadata !182, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %43, metadata !182, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 115, metadata !183, metadata !DIExpression()), !dbg !258
  %104 = inttoptr i32 %41 to i8*, !dbg !311
  %105 = getelementptr inbounds i8, i8* %104, i32 4, !dbg !311
  call void @llvm.dbg.value(metadata i32 %178, metadata !169, metadata !DIExpression()), !dbg !257
  %106 = inttoptr i32 %41 to i8**, !dbg !311
  %107 = load i8*, i8** %106, align 4, !dbg !311
  call void @llvm.dbg.value(metadata i8* %107, metadata !186, metadata !DIExpression()), !dbg !312
  %108 = ptrtoint i8* %107 to i32, !dbg !313
  call void @llvm.dbg.value(metadata i32 %108, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %108, i32* %5, align 4, !dbg !314, !tbaa !112
  call void @llvm.dbg.value(metadata i32 0, metadata !185, metadata !DIExpression()), !dbg !258
  %109 = add i32 %43, -1, !dbg !312
  br label %110, !dbg !315

110:                                              ; preds = %110, %103
  %111 = phi i32 [ 0, %103 ], [ %117, %110 ], !dbg !312
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  %112 = getelementptr inbounds i8, i8* %107, i32 %111, !dbg !316
  %113 = load i8, i8* %112, align 1, !dbg !316, !tbaa !273
  %114 = icmp eq i8 %113, 0, !dbg !316
  %115 = icmp ult i32 %109, %111, !dbg !317
  %116 = or i1 %115, %114, !dbg !318
  %117 = add i32 %111, 1, !dbg !319
  call void @llvm.dbg.value(metadata i32 %117, metadata !185, metadata !DIExpression()), !dbg !258
  br i1 %116, label %177, label %110, !dbg !318, !llvm.loop !321

118:                                              ; preds = %87, %87
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 100, metadata !183, metadata !DIExpression()), !dbg !258
  %119 = inttoptr i32 %41 to i8*, !dbg !323
  %120 = getelementptr inbounds i8, i8* %119, i32 4, !dbg !323
  call void @llvm.dbg.value(metadata i32 %132, metadata !169, metadata !DIExpression()), !dbg !257
  %121 = inttoptr i32 %41 to i32*, !dbg !323
  %122 = load i32, i32* %121, align 4, !dbg !323
  call void @llvm.dbg.value(metadata i32 %122, metadata !198, metadata !DIExpression()), !dbg !324
  call void @llvm.dbg.value(metadata i32 %122, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %122, i32* %5, align 4, !dbg !325, !tbaa !112
  call void @llvm.dbg.value(metadata i32 0, metadata !185, metadata !DIExpression()), !dbg !258
  %123 = icmp slt i32 %122, 0, !dbg !326
  %124 = sub nsw i32 0, %122, !dbg !328
  %125 = lshr i32 %122, 31, !dbg !330
  %126 = select i1 %123, i32 %124, i32 %122, !dbg !330
  call void @llvm.dbg.value(metadata i32 %126, metadata !198, metadata !DIExpression()), !dbg !324
  call void @llvm.dbg.value(metadata i32 %125, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %126, metadata !201, metadata !DIExpression()), !dbg !331
  br label %127, !dbg !332

127:                                              ; preds = %135, %118
  %128 = phi i32 [ %125, %118 ], [ %136, %135 ], !dbg !324
  %129 = phi i32 [ %126, %118 ], [ %137, %135 ], !dbg !331
  call void @llvm.dbg.value(metadata i32 %129, metadata !201, metadata !DIExpression()), !dbg !331
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  %130 = icmp eq i32 %129, 0, !dbg !333
  br i1 %130, label %131, label %135, !dbg !335

131:                                              ; preds = %127
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  %132 = ptrtoint i8* %120 to i32, !dbg !323
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %128, metadata !185, metadata !DIExpression()), !dbg !258
  %133 = icmp eq i32 %128, 0, !dbg !336
  %134 = select i1 %133, i32 1, i32 %128, !dbg !338
  call void @llvm.dbg.value(metadata i32 %134, metadata !185, metadata !DIExpression()), !dbg !258
  br label %179

135:                                              ; preds = %127
  %136 = add i32 %128, 1, !dbg !339
  call void @llvm.dbg.value(metadata i32 %136, metadata !185, metadata !DIExpression()), !dbg !258
  %137 = udiv i32 %129, 10, !dbg !341
  call void @llvm.dbg.value(metadata i32 %137, metadata !201, metadata !DIExpression()), !dbg !331
  br label %127, !dbg !342, !llvm.loop !343

138:                                              ; preds = %87
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 117, metadata !183, metadata !DIExpression()), !dbg !258
  %139 = inttoptr i32 %41 to i8*, !dbg !345
  %140 = getelementptr inbounds i8, i8* %139, i32 4, !dbg !345
  call void @llvm.dbg.value(metadata i32 %148, metadata !169, metadata !DIExpression()), !dbg !257
  %141 = inttoptr i32 %41 to i32*, !dbg !345
  %142 = load i32, i32* %141, align 4, !dbg !345
  call void @llvm.dbg.value(metadata i32 %142, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %142, i32* %5, align 4, !dbg !346, !tbaa !112
  call void @llvm.dbg.value(metadata i32 0, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %142, metadata !203, metadata !DIExpression()), !dbg !347
  br label %143, !dbg !348

143:                                              ; preds = %151, %138
  %144 = phi i32 [ 0, %138 ], [ %152, %151 ], !dbg !349
  %145 = phi i32 [ %142, %138 ], [ %153, %151 ], !dbg !347
  call void @llvm.dbg.value(metadata i32 %145, metadata !203, metadata !DIExpression()), !dbg !347
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  %146 = icmp eq i32 %145, 0, !dbg !350
  br i1 %146, label %147, label %151, !dbg !352

147:                                              ; preds = %143
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  %148 = ptrtoint i8* %140 to i32, !dbg !345
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %144, metadata !185, metadata !DIExpression()), !dbg !258
  %149 = icmp eq i32 %144, 0, !dbg !353
  %150 = select i1 %149, i32 1, i32 %144, !dbg !355
  br label %179, !dbg !355

151:                                              ; preds = %143
  %152 = add i32 %144, 1, !dbg !356
  call void @llvm.dbg.value(metadata i32 %152, metadata !185, metadata !DIExpression()), !dbg !258
  %153 = udiv i32 %145, 10, !dbg !358
  call void @llvm.dbg.value(metadata i32 %153, metadata !203, metadata !DIExpression()), !dbg !347
  br label %143, !dbg !359, !llvm.loop !360

154:                                              ; preds = %87
  %155 = and i8 %70, -32, !dbg !362
  %156 = icmp eq i8 %155, 32, !dbg !362
  br i1 %156, label %67, label %157, !dbg !362, !llvm.loop !289

157:                                              ; preds = %154
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %56, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8* %68, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %41, metadata !169, metadata !DIExpression()), !dbg !257
  switch i8 %70, label %158 [
    i8 120, label %159
    i8 88, label %159
  ], !dbg !363

158:                                              ; preds = %157
  call void @llvm.dbg.value(metadata i8 1, metadata !177, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 8, metadata !181, metadata !DIExpression()), !dbg !258
  br label %159, !dbg !365

159:                                              ; preds = %158, %157, %157
  %160 = phi i32 [ %56, %157 ], [ 8, %158 ], [ %56, %157 ], !dbg !258
  %161 = phi i1 [ %53, %157 ], [ true, %158 ], [ %53, %157 ]
  call void @llvm.dbg.value(metadata i8 undef, metadata !177, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %160, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i8 120, metadata !183, metadata !DIExpression()), !dbg !258
  %162 = inttoptr i32 %41 to i8*, !dbg !367
  %163 = getelementptr inbounds i8, i8* %162, i32 4, !dbg !367
  call void @llvm.dbg.value(metadata i32 %171, metadata !169, metadata !DIExpression()), !dbg !257
  %164 = inttoptr i32 %41 to i32*, !dbg !367
  %165 = load i32, i32* %164, align 4, !dbg !367
  call void @llvm.dbg.value(metadata i32 %165, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %165, i32* %5, align 4, !dbg !368, !tbaa !112
  call void @llvm.dbg.value(metadata i32 0, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %165, metadata !207, metadata !DIExpression()), !dbg !369
  br label %166, !dbg !370

166:                                              ; preds = %174, %159
  %167 = phi i32 [ 0, %159 ], [ %175, %174 ], !dbg !371
  %168 = phi i32 [ %165, %159 ], [ %176, %174 ], !dbg !369
  call void @llvm.dbg.value(metadata i32 %168, metadata !207, metadata !DIExpression()), !dbg !369
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  %169 = icmp eq i32 %168, 0, !dbg !372
  br i1 %169, label %170, label %174, !dbg !374

170:                                              ; preds = %166
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  %171 = ptrtoint i8* %163 to i32, !dbg !367
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %167, metadata !185, metadata !DIExpression()), !dbg !258
  %172 = icmp eq i32 %167, 0, !dbg !375
  %173 = select i1 %172, i32 1, i32 %167, !dbg !377
  br label %179, !dbg !377

174:                                              ; preds = %166
  %175 = add nuw nsw i32 %167, 1, !dbg !378
  call void @llvm.dbg.value(metadata i32 %175, metadata !185, metadata !DIExpression()), !dbg !258
  %176 = lshr i32 %168, 4, !dbg !380
  call void @llvm.dbg.value(metadata i32 %176, metadata !207, metadata !DIExpression()), !dbg !369
  br label %166, !dbg !381, !llvm.loop !382

177:                                              ; preds = %110
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  %178 = ptrtoint i8* %105 to i32, !dbg !311
  call void @llvm.dbg.value(metadata i32 %111, metadata !185, metadata !DIExpression()), !dbg !258
  br label %179, !dbg !384

179:                                              ; preds = %177, %170, %147, %131, %97, %96
  %180 = phi i32 [ 99, %96 ], [ 99, %97 ], [ 100, %131 ], [ 117, %147 ], [ 120, %170 ], [ 115, %177 ]
  %181 = phi i32 [ 1, %96 ], [ 1, %97 ], [ %134, %131 ], [ %150, %147 ], [ %173, %170 ], [ %111, %177 ], !dbg !385
  %182 = phi i32 [ %56, %96 ], [ %56, %97 ], [ %56, %131 ], [ %56, %147 ], [ %160, %170 ], [ %56, %177 ], !dbg !386
  %183 = phi i1 [ %53, %96 ], [ %53, %97 ], [ %53, %131 ], [ %53, %147 ], [ %161, %170 ], [ %53, %177 ]
  %184 = phi i32 [ %41, %96 ], [ %100, %97 ], [ %132, %131 ], [ %148, %147 ], [ %171, %170 ], [ %178, %177 ]
  call void @llvm.dbg.value(metadata i32 %184, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8 undef, metadata !177, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %182, metadata !181, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %181, metadata !185, metadata !DIExpression()), !dbg !258
  %185 = getelementptr inbounds i8, i8* %68, i32 2, !dbg !384
  call void @llvm.dbg.value(metadata i8* %185, metadata !170, metadata !DIExpression()), !dbg !257
  br i1 %65, label %202, label %186, !dbg !387

186:                                              ; preds = %179
  %187 = sub nsw i32 %182, %181, !dbg !388
  %188 = select i1 %183, i8 48, i8 32, !dbg !389
  br label %189, !dbg !390

189:                                              ; preds = %199, %186
  %190 = phi i32 [ %201, %199 ], [ 0, %186 ], !dbg !391
  %191 = phi i32 [ %200, %199 ], [ %28, %186 ], !dbg !261
  %192 = phi i32 [ %197, %199 ], [ %29, %186 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %191, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %190, metadata !211, metadata !DIExpression()), !dbg !391
  %193 = icmp slt i32 %190, %187, !dbg !392
  br i1 %193, label %194, label %202, !dbg !390

194:                                              ; preds = %189
  call void @llvm.dbg.value(metadata i8* %6, metadata !215, metadata !DIExpression(DW_OP_deref)), !dbg !389
  call void @llvm.lifetime.start.p0i8(i64 1, i8* nonnull %6) #5, !dbg !393
  call void @llvm.dbg.value(metadata i8 %188, metadata !215, metadata !DIExpression()), !dbg !389
  store i8 %188, i8* %6, align 1, !dbg !394, !tbaa !273
  call void @llvm.dbg.value(metadata i8* %6, metadata !215, metadata !DIExpression(DW_OP_deref)), !dbg !389
  %195 = call i32 %0(i8* %1, i8* nonnull %6, i32 1) #11, !dbg !395
  call void @llvm.dbg.value(metadata i32 %195, metadata !218, metadata !DIExpression()), !dbg !389
  %196 = icmp slt i32 %195, 0, !dbg !396
  %197 = select i1 %196, i32 %195, i32 %192, !dbg !398
  call void @llvm.dbg.value(metadata i32 undef, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %6, metadata !215, metadata !DIExpression(DW_OP_deref)), !dbg !389
  call void @llvm.lifetime.end.p0i8(i64 1, i8* nonnull %6) #5, !dbg !399
  %198 = icmp sgt i32 %195, -1
  br i1 %198, label %199, label %301

199:                                              ; preds = %194
  %200 = add nsw i32 %195, %191, !dbg !398
  call void @llvm.dbg.value(metadata i32 %200, metadata !171, metadata !DIExpression()), !dbg !257
  %201 = add nuw nsw i32 %190, 1, !dbg !400
  call void @llvm.dbg.value(metadata i32 %201, metadata !211, metadata !DIExpression()), !dbg !391
  br label %189, !dbg !401, !llvm.loop !402

202:                                              ; preds = %189, %179
  %203 = phi i32 [ %28, %179 ], [ %191, %189 ], !dbg !261
  %204 = phi i32 [ %29, %179 ], [ %192, %189 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %203, metadata !171, metadata !DIExpression()), !dbg !257
  switch i32 %180, label %283 [
    i32 99, label %205
    i32 115, label %212
    i32 120, label %220
    i32 117, label %241
    i32 100, label %241
  ], !dbg !404

205:                                              ; preds = %202
  %206 = call i32 %0(i8* %1, i8* nonnull %11, i32 1) #11, !dbg !405
  call void @llvm.dbg.value(metadata i32 %206, metadata !219, metadata !DIExpression()), !dbg !406
  %207 = icmp slt i32 %206, 0, !dbg !407
  %208 = select i1 %207, i32 0, i32 %206, !dbg !409
  %209 = add nsw i32 %208, %203, !dbg !409
  %210 = select i1 %207, i32 %206, i32 %204, !dbg !409
  call void @llvm.dbg.value(metadata i32 %209, metadata !171, metadata !DIExpression()), !dbg !257
  %211 = icmp sgt i32 %206, -1
  br i1 %211, label %283, label %301

212:                                              ; preds = %202
  %213 = load i8*, i8** %12, align 4, !dbg !410, !tbaa !112
  %214 = call i32 %0(i8* %1, i8* %213, i32 %181) #11, !dbg !411
  call void @llvm.dbg.value(metadata i32 %214, metadata !222, metadata !DIExpression()), !dbg !259
  %215 = icmp slt i32 %214, 0, !dbg !412
  %216 = select i1 %215, i32 0, i32 %214, !dbg !414
  %217 = add nsw i32 %216, %203, !dbg !414
  %218 = select i1 %215, i32 %214, i32 %204, !dbg !414
  call void @llvm.dbg.value(metadata i32 %217, metadata !171, metadata !DIExpression()), !dbg !257
  %219 = icmp sgt i32 %214, -1
  br i1 %219, label %283, label %301

220:                                              ; preds = %226, %202
  %221 = phi i32 [ %224, %226 ], [ %181, %202 ]
  %222 = phi i32 [ %238, %226 ], [ %203, %202 ], !dbg !261
  %223 = phi i32 [ %239, %226 ], [ %204, %202 ], !dbg !258
  %224 = add i32 %221, -1, !dbg !415
  call void @llvm.dbg.value(metadata i32 %222, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %224, metadata !225, metadata !DIExpression()), !dbg !415
  %225 = icmp sgt i32 %224, -1, !dbg !416
  br i1 %225, label %226, label %283, !dbg !417

226:                                              ; preds = %220
  %227 = load i32, i32* %5, align 4, !dbg !418, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %227, metadata !184, metadata !DIExpression()), !dbg !258
  %228 = shl nsw i32 %224, 2, !dbg !419
  %229 = lshr i32 %227, %228, !dbg !420
  %230 = and i32 %229, 15, !dbg !421
  call void @llvm.dbg.value(metadata i32 %230, metadata !229, metadata !DIExpression()), !dbg !422
  call void @llvm.dbg.value(metadata i8* %7, metadata !232, metadata !DIExpression(DW_OP_deref)), !dbg !422
  call void @llvm.lifetime.start.p0i8(i64 1, i8* nonnull %7) #5, !dbg !423
  %231 = icmp ugt i32 %230, 9, !dbg !424
  %232 = select i1 %231, i32 87, i32 48, !dbg !425
  %233 = add nuw nsw i32 %232, %230, !dbg !426
  %234 = trunc i32 %233 to i8, !dbg !427
  call void @llvm.dbg.value(metadata i8 %234, metadata !232, metadata !DIExpression()), !dbg !422
  store i8 %234, i8* %7, align 1, !dbg !428, !tbaa !273
  call void @llvm.dbg.value(metadata i8* %7, metadata !232, metadata !DIExpression(DW_OP_deref)), !dbg !422
  %235 = call i32 %0(i8* %1, i8* nonnull %7, i32 1) #11, !dbg !429
  call void @llvm.dbg.value(metadata i32 %235, metadata !233, metadata !DIExpression()), !dbg !422
  %236 = icmp slt i32 %235, 0, !dbg !430
  %237 = select i1 %236, i32 0, i32 %235, !dbg !432
  %238 = add nsw i32 %237, %222, !dbg !432
  %239 = select i1 %236, i32 %235, i32 %223, !dbg !432
  call void @llvm.dbg.value(metadata i32 %238, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %7, metadata !232, metadata !DIExpression(DW_OP_deref)), !dbg !422
  call void @llvm.lifetime.end.p0i8(i64 1, i8* nonnull %7) #5, !dbg !433
  %240 = icmp sgt i32 %235, -1
  br i1 %240, label %220, label %301, !llvm.loop !434

241:                                              ; preds = %202, %202
  %242 = icmp eq i32 %180, 100, !dbg !436
  %243 = add i32 %181, -1, !dbg !437
  call void @llvm.dbg.value(metadata i32 %243, metadata !234, metadata !DIExpression()), !dbg !438
  %244 = load i32, i32* %5, align 4, !dbg !439
  call void @llvm.dbg.value(metadata i32 %244, metadata !184, metadata !DIExpression()), !dbg !258
  %245 = icmp slt i32 %244, 0, !dbg !440
  %246 = and i1 %242, %245, !dbg !441
  br i1 %246, label %247, label %255, !dbg !441

247:                                              ; preds = %241
  %248 = call i32 %0(i8* %1, i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str.2, i32 0, i32 0), i32 1) #11, !dbg !442
  call void @llvm.dbg.value(metadata i32 %248, metadata !237, metadata !DIExpression()), !dbg !443
  %249 = icmp slt i32 %248, 0, !dbg !444
  br i1 %249, label %301, label %250, !dbg !446

250:                                              ; preds = %247
  %251 = add nsw i32 %248, %203, !dbg !447
  call void @llvm.dbg.value(metadata i32 %251, metadata !171, metadata !DIExpression()), !dbg !257
  %252 = load i32, i32* %5, align 4, !dbg !448, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %252, metadata !184, metadata !DIExpression()), !dbg !258
  %253 = sub i32 0, %252, !dbg !449
  call void @llvm.dbg.value(metadata i32 %253, metadata !184, metadata !DIExpression()), !dbg !258
  store i32 %253, i32* %5, align 4, !dbg !450, !tbaa !112
  %254 = add i32 %181, -2, !dbg !451
  call void @llvm.dbg.value(metadata i32 %254, metadata !234, metadata !DIExpression()), !dbg !438
  br label %255

255:                                              ; preds = %250, %241
  %256 = phi i32 [ %254, %250 ], [ %243, %241 ]
  %257 = phi i32 [ %251, %250 ], [ %203, %241 ]
  br label %258, !dbg !452

258:                                              ; preds = %280, %255
  %259 = phi i32 [ %282, %280 ], [ %256, %255 ], !dbg !438
  %260 = phi i32 [ %281, %280 ], [ %257, %255 ], !dbg !261
  %261 = phi i32 [ %275, %280 ], [ %204, %255 ], !dbg !438
  call void @llvm.dbg.value(metadata i32 %260, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %259, metadata !234, metadata !DIExpression()), !dbg !438
  %262 = icmp sgt i32 %259, -1, !dbg !453
  br i1 %262, label %263, label %283, !dbg !452

263:                                              ; preds = %258
  %264 = load i32, i32* %5, align 4, !dbg !454, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %264, metadata !184, metadata !DIExpression()), !dbg !258
  call void @llvm.dbg.value(metadata i32 %264, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 0, metadata !244, metadata !DIExpression()), !dbg !456
  br label %265, !dbg !457

265:                                              ; preds = %277, %263
  %266 = phi i32 [ %264, %263 ], [ %278, %277 ], !dbg !455
  %267 = phi i32 [ 0, %263 ], [ %279, %277 ], !dbg !456
  call void @llvm.dbg.value(metadata i32 %267, metadata !244, metadata !DIExpression()), !dbg !456
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  %268 = icmp eq i32 %267, %259, !dbg !458
  br i1 %268, label %269, label %277, !dbg !460

269:                                              ; preds = %265
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i32 %266, metadata !240, metadata !DIExpression()), !dbg !455
  %270 = urem i32 %266, 10, !dbg !461
  call void @llvm.dbg.value(metadata i32 %270, metadata !246, metadata !DIExpression()), !dbg !455
  call void @llvm.dbg.value(metadata i8* %8, metadata !247, metadata !DIExpression(DW_OP_deref)), !dbg !455
  call void @llvm.lifetime.start.p0i8(i64 1, i8* nonnull %8) #5, !dbg !462
  %271 = trunc i32 %270 to i8, !dbg !463
  %272 = or i8 %271, 48, !dbg !463
  call void @llvm.dbg.value(metadata i8 %272, metadata !247, metadata !DIExpression()), !dbg !455
  store i8 %272, i8* %8, align 1, !dbg !464, !tbaa !273
  call void @llvm.dbg.value(metadata i8* %8, metadata !247, metadata !DIExpression(DW_OP_deref)), !dbg !455
  %273 = call i32 %0(i8* %1, i8* nonnull %8, i32 1) #11, !dbg !465
  call void @llvm.dbg.value(metadata i32 %273, metadata !248, metadata !DIExpression()), !dbg !455
  %274 = icmp slt i32 %273, 0, !dbg !466
  %275 = select i1 %274, i32 %273, i32 %261, !dbg !468
  call void @llvm.dbg.value(metadata i32 undef, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %8, metadata !247, metadata !DIExpression(DW_OP_deref)), !dbg !455
  call void @llvm.lifetime.end.p0i8(i64 1, i8* nonnull %8) #5, !dbg !469
  %276 = icmp sgt i32 %273, -1
  br i1 %276, label %280, label %301

277:                                              ; preds = %265
  %278 = udiv i32 %266, 10, !dbg !470
  call void @llvm.dbg.value(metadata i32 %278, metadata !240, metadata !DIExpression()), !dbg !455
  %279 = add nuw i32 %267, 1, !dbg !472
  call void @llvm.dbg.value(metadata i32 %279, metadata !244, metadata !DIExpression()), !dbg !456
  br label %265, !dbg !473, !llvm.loop !474

280:                                              ; preds = %269
  %281 = add nsw i32 %273, %260, !dbg !468
  call void @llvm.dbg.value(metadata i32 %281, metadata !171, metadata !DIExpression()), !dbg !257
  %282 = add nsw i32 %259, -1, !dbg !476
  call void @llvm.dbg.value(metadata i32 %282, metadata !234, metadata !DIExpression()), !dbg !438
  br label %258, !dbg !477, !llvm.loop !478

283:                                              ; preds = %258, %220, %212, %205, %202
  %284 = phi i32 [ %209, %205 ], [ %217, %212 ], [ %203, %202 ], [ %222, %220 ], [ %260, %258 ], !dbg !261
  %285 = phi i32 [ %210, %205 ], [ %218, %212 ], [ %204, %202 ], [ %223, %220 ], [ %261, %258 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %284, metadata !171, metadata !DIExpression()), !dbg !257
  br i1 %65, label %286, label %303, !dbg !480

286:                                              ; preds = %283
  %287 = sub nsw i32 %182, %181, !dbg !481
  br label %288, !dbg !482

288:                                              ; preds = %298, %286
  %289 = phi i32 [ %299, %298 ], [ %284, %286 ], !dbg !261
  %290 = phi i32 [ %300, %298 ], [ 0, %286 ], !dbg !483
  %291 = phi i32 [ %296, %298 ], [ %285, %286 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %290, metadata !249, metadata !DIExpression()), !dbg !483
  call void @llvm.dbg.value(metadata i32 %289, metadata !171, metadata !DIExpression()), !dbg !257
  %292 = icmp slt i32 %290, %287, !dbg !484
  br i1 %292, label %293, label %303, !dbg !482

293:                                              ; preds = %288
  call void @llvm.dbg.value(metadata i8* %9, metadata !253, metadata !DIExpression(DW_OP_deref)), !dbg !485
  call void @llvm.lifetime.start.p0i8(i64 1, i8* nonnull %9) #5, !dbg !486
  call void @llvm.dbg.value(metadata i8 32, metadata !253, metadata !DIExpression()), !dbg !485
  store i8 32, i8* %9, align 1, !dbg !487, !tbaa !273
  call void @llvm.dbg.value(metadata i8* %9, metadata !253, metadata !DIExpression(DW_OP_deref)), !dbg !485
  %294 = call i32 %0(i8* %1, i8* nonnull %9, i32 1) #11, !dbg !488
  call void @llvm.dbg.value(metadata i32 %294, metadata !256, metadata !DIExpression()), !dbg !485
  %295 = icmp slt i32 %294, 0, !dbg !489
  %296 = select i1 %295, i32 %294, i32 %291, !dbg !491
  call void @llvm.dbg.value(metadata i32 undef, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %9, metadata !253, metadata !DIExpression(DW_OP_deref)), !dbg !485
  call void @llvm.lifetime.end.p0i8(i64 1, i8* nonnull %9) #5, !dbg !492
  %297 = icmp sgt i32 %294, -1
  br i1 %297, label %298, label %301

298:                                              ; preds = %293
  %299 = add nsw i32 %294, %289, !dbg !491
  call void @llvm.dbg.value(metadata i32 %299, metadata !171, metadata !DIExpression()), !dbg !257
  %300 = add nuw nsw i32 %290, 1, !dbg !493
  call void @llvm.dbg.value(metadata i32 %300, metadata !249, metadata !DIExpression()), !dbg !483
  br label %288, !dbg !494, !llvm.loop !495

301:                                              ; preds = %293, %269, %247, %226, %212, %205, %194
  %302 = phi i32 [ %296, %293 ], [ %239, %226 ], [ %275, %269 ], [ %197, %194 ], [ %218, %212 ], [ %210, %205 ], [ %248, %247 ]
  call void @llvm.dbg.value(metadata i32 %304, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.lifetime.end.p0i8(i64 4, i8* nonnull %11) #5, !dbg !497
  call void @llvm.dbg.value(metadata i32 %184, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %185, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %304, metadata !171, metadata !DIExpression()), !dbg !257
  br label %306

303:                                              ; preds = %288, %283
  %304 = phi i32 [ %284, %283 ], [ %289, %288 ], !dbg !261
  %305 = phi i32 [ %285, %283 ], [ %291, %288 ], !dbg !258
  call void @llvm.dbg.value(metadata i32 %304, metadata !171, metadata !DIExpression()), !dbg !257
  call void @llvm.lifetime.end.p0i8(i64 4, i8* nonnull %11) #5, !dbg !497
  call void @llvm.dbg.value(metadata i32 %184, metadata !169, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i8* %185, metadata !170, metadata !DIExpression()), !dbg !257
  call void @llvm.dbg.value(metadata i32 %304, metadata !171, metadata !DIExpression()), !dbg !257
  br label %13

306:                                              ; preds = %301, %27, %20
  %307 = phi i32 [ %302, %301 ], [ %25, %20 ], [ %28, %27 ]
  ret i32 %307, !dbg !498
}

; Function Attrs: minsize optsize
declare dso_local i32 @strcspn(i8*, i8*) local_unnamed_addr #3

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__wrap_vprintf(i8*, [1 x i32]) #4 !dbg !499 {
  call void @llvm.dbg.value(metadata i32 undef, metadata !504, metadata !DIExpression()), !dbg !505
  call void @llvm.dbg.value(metadata i8* %0, metadata !503, metadata !DIExpression()), !dbg !505
  %3 = tail call i32 @__box_cbprintf(i32 (i8*, i8*, i32)* nonnull @__box_vprintf_write, i8* nonnull inttoptr (i32 1 to i8*), i8* %0, [1 x i32] %1) #12, !dbg !506
  ret i32 %3, !dbg !507
}

; Function Attrs: minsize nounwind optsize
define internal i32 @__box_vprintf_write(i8*, i8*, i32) #4 !dbg !508 {
  call void @llvm.dbg.value(metadata i8* %0, metadata !510, metadata !DIExpression()), !dbg !513
  call void @llvm.dbg.value(metadata i8* %1, metadata !511, metadata !DIExpression()), !dbg !513
  call void @llvm.dbg.value(metadata i32 %2, metadata !512, metadata !DIExpression()), !dbg !513
  %4 = ptrtoint i8* %0 to i32, !dbg !514
  %5 = ptrtoint i8* %1 to i32, !dbg !515
  call void @llvm.dbg.value(metadata i32 %4, metadata !516, metadata !DIExpression()) #5, !dbg !523
  call void @llvm.dbg.value(metadata i32 %5, metadata !521, metadata !DIExpression()) #5, !dbg !523
  call void @llvm.dbg.value(metadata i32 %2, metadata !522, metadata !DIExpression()) #5, !dbg !523
  %6 = load i32*, i32** @__box_importjumptable, align 4, !dbg !525, !tbaa !91
  %7 = getelementptr inbounds i32, i32* %6, i32 1, !dbg !525
  %8 = bitcast i32* %7 to i32 (i32, i8*, i32)**, !dbg !525
  %9 = load i32 (i32, i8*, i32)*, i32 (i32, i8*, i32)** %8, align 4, !dbg !525, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %5, metadata !526, metadata !DIExpression()) #5, !dbg !531
  %10 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %5, !dbg !533
  %11 = tail call i32 %9(i32 %4, i8* nonnull %10, i32 %2) #11, !dbg !534
  ret i32 %11, !dbg !535
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__wrap_printf(i8*, ...) #4 !dbg !536 {
  %2 = alloca %struct.__va_list, align 4
  call void @llvm.dbg.value(metadata i8* %0, metadata !540, metadata !DIExpression()), !dbg !543
  %3 = bitcast %struct.__va_list* %2 to i8*, !dbg !544
  call void @llvm.lifetime.start.p0i8(i64 4, i8* nonnull %3) #5, !dbg !544
  call void @llvm.va_start(i8* nonnull %3), !dbg !545
  %4 = bitcast %struct.__va_list* %2 to i32*, !dbg !546
  %5 = load i32, i32* %4, align 4, !dbg !546
  %6 = insertvalue [1 x i32] undef, i32 %5, 0, !dbg !546
  %7 = call i32 @__wrap_vprintf(i8* %0, [1 x i32] %6) #12, !dbg !546
  call void @llvm.dbg.value(metadata i32 %7, metadata !542, metadata !DIExpression()), !dbg !543
  call void @llvm.va_end(i8* nonnull %3), !dbg !547
  call void @llvm.lifetime.end.p0i8(i64 4, i8* nonnull %3) #5, !dbg !548
  ret i32 %7, !dbg !549
}

; Function Attrs: nounwind
declare void @llvm.va_start(i8*) #5

; Function Attrs: nounwind
declare void @llvm.va_end(i8*) #5

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__wrap_vfprintf(%struct.__sFILE* readnone, i8*, [1 x i32]) #4 !dbg !550 {
  call void @llvm.dbg.value(metadata i32 undef, metadata !764, metadata !DIExpression()), !dbg !766
  call void @llvm.dbg.value(metadata %struct.__sFILE* %0, metadata !762, metadata !DIExpression()), !dbg !766
  call void @llvm.dbg.value(metadata i8* %1, metadata !763, metadata !DIExpression()), !dbg !766
  %4 = load %struct._reent*, %struct._reent** @_impure_ptr, align 4, !dbg !767, !tbaa !91
  %5 = getelementptr inbounds %struct._reent, %struct._reent* %4, i32 0, i32 2, !dbg !767
  %6 = load %struct.__sFILE*, %struct.__sFILE** %5, align 8, !dbg !767, !tbaa !768
  %7 = icmp eq %struct.__sFILE* %6, %0, !dbg !774
  %8 = select i1 %7, i8* inttoptr (i32 1 to i8*), i8* inttoptr (i32 2 to i8*), !dbg !775
  call void @llvm.dbg.value(metadata i8* %8, metadata !765, metadata !DIExpression()), !dbg !766
  %9 = tail call i32 @__box_cbprintf(i32 (i8*, i8*, i32)* nonnull @__box_vprintf_write, i8* nonnull %8, i8* %1, [1 x i32] %2) #12, !dbg !776
  ret i32 %9, !dbg !777
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__wrap_fprintf(%struct.__sFILE* readnone, i8*, ...) #4 !dbg !778 {
  %3 = alloca %struct.__va_list, align 4
  call void @llvm.dbg.value(metadata %struct.__sFILE* %0, metadata !782, metadata !DIExpression()), !dbg !786
  call void @llvm.dbg.value(metadata i8* %1, metadata !783, metadata !DIExpression()), !dbg !786
  %4 = bitcast %struct.__va_list* %3 to i8*, !dbg !787
  call void @llvm.lifetime.start.p0i8(i64 4, i8* nonnull %4) #5, !dbg !787
  call void @llvm.va_start(i8* nonnull %4), !dbg !788
  %5 = bitcast %struct.__va_list* %3 to i32*, !dbg !789
  %6 = load i32, i32* %5, align 4, !dbg !789
  %7 = insertvalue [1 x i32] undef, i32 %6, 0, !dbg !789
  %8 = call i32 @__wrap_vfprintf(%struct.__sFILE* %0, i8* %1, [1 x i32] %7) #12, !dbg !789
  call void @llvm.dbg.value(metadata i32 %8, metadata !785, metadata !DIExpression()), !dbg !786
  call void @llvm.va_end(i8* nonnull %4), !dbg !790
  call void @llvm.lifetime.end.p0i8(i64 4, i8* nonnull %4) #5, !dbg !791
  ret i32 %8, !dbg !792
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__wrap_fflush(%struct.__sFILE* readnone) #4 !dbg !793 {
  call void @llvm.dbg.value(metadata %struct.__sFILE* %0, metadata !797, metadata !DIExpression()), !dbg !799
  %2 = load %struct._reent*, %struct._reent** @_impure_ptr, align 4, !dbg !800, !tbaa !91
  %3 = getelementptr inbounds %struct._reent, %struct._reent* %2, i32 0, i32 2, !dbg !800
  %4 = load %struct.__sFILE*, %struct.__sFILE** %3, align 8, !dbg !800, !tbaa !768
  %5 = icmp eq %struct.__sFILE* %4, %0, !dbg !801
  %6 = select i1 %5, i32 1, i32 2, !dbg !802
  call void @llvm.dbg.value(metadata i32 %6, metadata !798, metadata !DIExpression()), !dbg !799
  call void @llvm.dbg.value(metadata i32 %6, metadata !803, metadata !DIExpression()) #5, !dbg !808
  %7 = load i32*, i32** @__box_importjumptable, align 4, !dbg !810, !tbaa !91
  %8 = getelementptr inbounds i32, i32* %7, i32 2, !dbg !810
  %9 = bitcast i32* %8 to i32 (i32)**, !dbg !810
  %10 = load i32 (i32)*, i32 (i32)** %9, align 4, !dbg !810, !tbaa !112
  %11 = tail call i32 %10(i32 %6) #11, !dbg !811
  ret i32 %11, !dbg !812
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @_write(i32, i8*, i32) local_unnamed_addr #4 !dbg !813 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !817, metadata !DIExpression()), !dbg !820
  call void @llvm.dbg.value(metadata i8* %1, metadata !818, metadata !DIExpression()), !dbg !820
  call void @llvm.dbg.value(metadata i32 %2, metadata !819, metadata !DIExpression()), !dbg !820
  %4 = ptrtoint i8* %1 to i32, !dbg !821
  call void @llvm.dbg.value(metadata i32 %0, metadata !516, metadata !DIExpression()) #5, !dbg !822
  call void @llvm.dbg.value(metadata i32 %4, metadata !521, metadata !DIExpression()) #5, !dbg !822
  call void @llvm.dbg.value(metadata i32 %2, metadata !522, metadata !DIExpression()) #5, !dbg !822
  %5 = load i32*, i32** @__box_importjumptable, align 4, !dbg !824, !tbaa !91
  %6 = getelementptr inbounds i32, i32* %5, i32 1, !dbg !824
  %7 = bitcast i32* %6 to i32 (i32, i8*, i32)**, !dbg !824
  %8 = load i32 (i32, i8*, i32)*, i32 (i32, i8*, i32)** %7, align 4, !dbg !824, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %4, metadata !526, metadata !DIExpression()) #5, !dbg !825
  %9 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %4, !dbg !827
  %10 = tail call i32 %8(i32 %0, i8* nonnull %9, i32 %2) #11, !dbg !828
  ret i32 %10, !dbg !829
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readnone
define dso_local nonnull i8* @to_ptr(i32) local_unnamed_addr #6 !dbg !527 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !526, metadata !DIExpression()), !dbg !830
  %2 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %0, !dbg !831
  ret i8* %2, !dbg !832
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readnone
define dso_local i32 @from_ptr(i8*) local_unnamed_addr #6 !dbg !833 {
  call void @llvm.dbg.value(metadata i8* %0, metadata !837, metadata !DIExpression()), !dbg !838
  %2 = ptrtoint i8* %0 to i32, !dbg !839
  %3 = sub i32 %2, ptrtoint ([0 x i8]* @__memory to i32), !dbg !839
  ret i32 %3, !dbg !840
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local signext i8 @get_i8(i32) local_unnamed_addr #7 !dbg !841 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !845, metadata !DIExpression()), !dbg !846
  %2 = and i32 %0, 65535, !dbg !847
  call void @llvm.dbg.value(metadata i32 %2, metadata !845, metadata !DIExpression()), !dbg !846
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !848
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !850
  %4 = load i8, i8* %3, align 1, !dbg !851, !tbaa !273
  ret i8 %4, !dbg !852
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local signext i16 @get_i16(i32) local_unnamed_addr #7 !dbg !853 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !857, metadata !DIExpression()), !dbg !858
  %2 = and i32 %0, 65535, !dbg !859
  call void @llvm.dbg.value(metadata i32 %2, metadata !857, metadata !DIExpression()), !dbg !858
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !860
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !862
  %4 = bitcast i8* %3 to i16*, !dbg !863
  %5 = load i16, i16* %4, align 2, !dbg !864, !tbaa !865
  ret i16 %5, !dbg !867
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local i32 @get_i32(i32) local_unnamed_addr #7 !dbg !868 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !872, metadata !DIExpression()), !dbg !873
  %2 = and i32 %0, 65535, !dbg !874
  call void @llvm.dbg.value(metadata i32 %2, metadata !872, metadata !DIExpression()), !dbg !873
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !875
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !877
  %4 = bitcast i8* %3 to i32*, !dbg !878
  %5 = load i32, i32* %4, align 4, !dbg !879, !tbaa !112
  ret i32 %5, !dbg !880
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local i64 @get_i64(i32) local_unnamed_addr #7 !dbg !881 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !885, metadata !DIExpression()), !dbg !886
  %2 = and i32 %0, 65535, !dbg !887
  call void @llvm.dbg.value(metadata i32 %2, metadata !885, metadata !DIExpression()), !dbg !886
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !888
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !890
  %4 = bitcast i8* %3 to i64*, !dbg !891
  %5 = load i64, i64* %4, align 8, !dbg !892, !tbaa !893
  ret i64 %5, !dbg !895
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local float @get_f32(i32) local_unnamed_addr #7 !dbg !896 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !900, metadata !DIExpression()), !dbg !901
  %2 = and i32 %0, 65535, !dbg !902
  call void @llvm.dbg.value(metadata i32 %2, metadata !900, metadata !DIExpression()), !dbg !901
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !903
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !905
  %4 = bitcast i8* %3 to float*, !dbg !906
  %5 = load float, float* %4, align 4, !dbg !907, !tbaa !908
  ret float %5, !dbg !910
}

; Function Attrs: alwaysinline minsize norecurse nounwind optsize readonly
define dso_local double @get_f64(i32) local_unnamed_addr #7 !dbg !911 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !915, metadata !DIExpression()), !dbg !916
  %2 = and i32 %0, 65535, !dbg !917
  call void @llvm.dbg.value(metadata i32 %2, metadata !915, metadata !DIExpression()), !dbg !916
  call void @llvm.dbg.value(metadata i32 %2, metadata !526, metadata !DIExpression()), !dbg !918
  %3 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %2, !dbg !920
  %4 = bitcast i8* %3 to double*, !dbg !921
  %5 = load double, double* %4, align 8, !dbg !922, !tbaa !923
  ret double %5, !dbg !925
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_i8(i32, i8 signext) local_unnamed_addr #8 !dbg !926 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !930, metadata !DIExpression()), !dbg !932
  call void @llvm.dbg.value(metadata i8 %1, metadata !931, metadata !DIExpression()), !dbg !932
  %3 = and i32 %0, 65535, !dbg !933
  call void @llvm.dbg.value(metadata i32 %3, metadata !930, metadata !DIExpression()), !dbg !932
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !934
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !936
  store i8 %1, i8* %4, align 1, !dbg !937, !tbaa !273
  ret void, !dbg !938
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_i16(i32, i16 signext) local_unnamed_addr #8 !dbg !939 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !943, metadata !DIExpression()), !dbg !945
  call void @llvm.dbg.value(metadata i16 %1, metadata !944, metadata !DIExpression()), !dbg !945
  %3 = and i32 %0, 65535, !dbg !946
  call void @llvm.dbg.value(metadata i32 %3, metadata !943, metadata !DIExpression()), !dbg !945
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !947
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !949
  %5 = bitcast i8* %4 to i16*, !dbg !950
  store i16 %1, i16* %5, align 2, !dbg !951, !tbaa !865
  ret void, !dbg !952
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_i32(i32, i32) local_unnamed_addr #8 !dbg !953 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !957, metadata !DIExpression()), !dbg !959
  call void @llvm.dbg.value(metadata i32 %1, metadata !958, metadata !DIExpression()), !dbg !959
  %3 = and i32 %0, 65535, !dbg !960
  call void @llvm.dbg.value(metadata i32 %3, metadata !957, metadata !DIExpression()), !dbg !959
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !961
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !963
  %5 = bitcast i8* %4 to i32*, !dbg !964
  store i32 %1, i32* %5, align 4, !dbg !965, !tbaa !112
  ret void, !dbg !966
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_i64(i32, i64) local_unnamed_addr #8 !dbg !967 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !971, metadata !DIExpression()), !dbg !973
  call void @llvm.dbg.value(metadata i64 %1, metadata !972, metadata !DIExpression()), !dbg !973
  %3 = and i32 %0, 65535, !dbg !974
  call void @llvm.dbg.value(metadata i32 %3, metadata !971, metadata !DIExpression()), !dbg !973
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !975
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !977
  %5 = bitcast i8* %4 to i64*, !dbg !978
  store i64 %1, i64* %5, align 8, !dbg !979, !tbaa !893
  ret void, !dbg !980
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_f32(i32, float) local_unnamed_addr #8 !dbg !981 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !985, metadata !DIExpression()), !dbg !987
  call void @llvm.dbg.value(metadata float %1, metadata !986, metadata !DIExpression()), !dbg !987
  %3 = and i32 %0, 65535, !dbg !988
  call void @llvm.dbg.value(metadata i32 %3, metadata !985, metadata !DIExpression()), !dbg !987
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !989
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !991
  %5 = bitcast i8* %4 to float*, !dbg !992
  store float %1, float* %5, align 4, !dbg !993, !tbaa !908
  ret void, !dbg !994
}

; Function Attrs: alwaysinline minsize nofree norecurse nounwind optsize writeonly
define dso_local void @set_f64(i32, double) local_unnamed_addr #8 !dbg !995 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !999, metadata !DIExpression()), !dbg !1001
  call void @llvm.dbg.value(metadata double %1, metadata !1000, metadata !DIExpression()), !dbg !1001
  %3 = and i32 %0, 65535, !dbg !1002
  call void @llvm.dbg.value(metadata i32 %3, metadata !999, metadata !DIExpression()), !dbg !1001
  call void @llvm.dbg.value(metadata i32 %3, metadata !526, metadata !DIExpression()), !dbg !1003
  %4 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %3, !dbg !1005
  %5 = bitcast i8* %4 to double*, !dbg !1006
  store double %1, double* %5, align 8, !dbg !1007, !tbaa !923
  ret void, !dbg !1008
}

; Function Attrs: alwaysinline minsize nounwind optsize
define dso_local nonnull i8* @get_memory_ptr_for_runtime(i32, i32) local_unnamed_addr #9 !dbg !1009 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !1013, metadata !DIExpression()), !dbg !1015
  call void @llvm.dbg.value(metadata i32 %1, metadata !1014, metadata !DIExpression()), !dbg !1015
  %3 = sub i32 65536, %1, !dbg !1016
  %4 = icmp ult i32 %3, %0, !dbg !1018
  br i1 %4, label %5, label %8, !dbg !1019, !prof !1020

5:                                                ; preds = %2
  call void @llvm.dbg.value(metadata i32 -14, metadata !104, metadata !DIExpression()) #5, !dbg !1021
  %6 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1024, !tbaa !91
  %7 = load void (i32)*, void (i32)** %6, align 4, !dbg !1024, !tbaa !112
  tail call void %7(i32 -14) #11, !dbg !1025
  unreachable, !dbg !1026

8:                                                ; preds = %2
  call void @llvm.dbg.value(metadata i32 %0, metadata !526, metadata !DIExpression()), !dbg !1027
  %9 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %0, !dbg !1029
  ret i8* %9, !dbg !1030
}

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @expand_memory() local_unnamed_addr #2 !dbg !1031 {
  call void @llvm.dbg.value(metadata i32 -12, metadata !104, metadata !DIExpression()) #5, !dbg !1032
  %1 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1034, !tbaa !91
  %2 = load void (i32)*, void (i32)** %1, align 4, !dbg !1034, !tbaa !112
  tail call void %2(i32 -12) #11, !dbg !1035
  unreachable, !dbg !1036
}

; Function Attrs: alwaysinline minsize nounwind optsize
define dso_local i8* @get_function_from_table(i32, i32) local_unnamed_addr #9 !dbg !1037 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !1041, metadata !DIExpression()), !dbg !1048
  call void @llvm.dbg.value(metadata i32 %1, metadata !1042, metadata !DIExpression()), !dbg !1048
  %3 = icmp ugt i32 %0, 511, !dbg !1049
  br i1 %3, label %4, label %7, !dbg !1051, !prof !1020

4:                                                ; preds = %2
  call void @llvm.dbg.value(metadata i32 -14, metadata !104, metadata !DIExpression()) #5, !dbg !1052
  %5 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1055, !tbaa !91
  %6 = load void (i32)*, void (i32)** %5, align 4, !dbg !1055, !tbaa !112
  tail call void %6(i32 -14) #11, !dbg !1056
  unreachable, !dbg !1057

7:                                                ; preds = %2
  %8 = getelementptr inbounds [0 x %struct.table_entry], [0 x %struct.table_entry]* @__table, i32 0, i32 %0, i32 0, !dbg !1058
  %9 = load i32, i32* %8, align 4, !dbg !1058
  call void @llvm.dbg.value(metadata i32 %9, metadata !1043, metadata !DIExpression(DW_OP_LLVM_fragment, 0, 32)), !dbg !1048
  %10 = getelementptr inbounds [0 x %struct.table_entry], [0 x %struct.table_entry]* @__table, i32 0, i32 %0, i32 1, !dbg !1058
  %11 = load i8*, i8** %10, align 4, !dbg !1058
  call void @llvm.dbg.value(metadata i8* %11, metadata !1043, metadata !DIExpression(DW_OP_LLVM_fragment, 32, 32)), !dbg !1048
  %12 = icmp ne i32 %9, %1, !dbg !1059
  %13 = icmp eq i8* %11, null, !dbg !1061
  %14 = or i1 %12, %13, !dbg !1062
  br i1 %14, label %15, label %18, !dbg !1063, !prof !1020

15:                                               ; preds = %7
  call void @llvm.dbg.value(metadata i32 -14, metadata !104, metadata !DIExpression()) #5, !dbg !1064
  %16 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1067, !tbaa !91
  %17 = load void (i32)*, void (i32)** %16, align 4, !dbg !1067, !tbaa !112
  tail call void %17(i32 -14) #11, !dbg !1068
  unreachable, !dbg !1069

18:                                               ; preds = %7
  ret i8* %11, !dbg !1070
}

; Function Attrs: minsize nounwind optsize
define dso_local void @add_function_to_table(i32, i32, i8*) local_unnamed_addr #4 !dbg !1071 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !1075, metadata !DIExpression()), !dbg !1078
  call void @llvm.dbg.value(metadata i32 %1, metadata !1076, metadata !DIExpression()), !dbg !1078
  call void @llvm.dbg.value(metadata i8* %2, metadata !1077, metadata !DIExpression()), !dbg !1078
  %4 = icmp ugt i32 %0, 511, !dbg !1079
  br i1 %4, label %5, label %8, !dbg !1081, !prof !1020

5:                                                ; preds = %3
  call void @llvm.dbg.value(metadata i32 -14, metadata !104, metadata !DIExpression()) #5, !dbg !1082
  %6 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1085, !tbaa !91
  %7 = load void (i32)*, void (i32)** %6, align 4, !dbg !1085, !tbaa !112
  tail call void %7(i32 -14) #11, !dbg !1086
  unreachable, !dbg !1087

8:                                                ; preds = %3
  %9 = getelementptr inbounds [0 x %struct.table_entry], [0 x %struct.table_entry]* @__table, i32 0, i32 %0, i32 0, !dbg !1088
  store i32 %1, i32* %9, align 4, !dbg !1089, !tbaa !1090
  %10 = getelementptr inbounds [0 x %struct.table_entry], [0 x %struct.table_entry]* @__table, i32 0, i32 %0, i32 1, !dbg !1092
  store i8* %2, i8** %10, align 4, !dbg !1093, !tbaa !1094
  ret void, !dbg !1095
}

; Function Attrs: minsize nounwind optsize
define dso_local void @clear_table() local_unnamed_addr #4 !dbg !1096 {
  %1 = tail call i8* @memset(i8* bitcast ([0 x %struct.table_entry]* @__table to i8*), i32 0, i32 4096) #11, !dbg !1097
  ret void, !dbg !1098
}

; Function Attrs: minsize optsize
declare dso_local i8* @memset(i8*, i32, i32) local_unnamed_addr #3

; Function Attrs: minsize noreturn nounwind optsize
define dso_local void @env___box_abort(i32) #2 !dbg !105 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !104, metadata !DIExpression()), !dbg !1099
  %2 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1100, !tbaa !91
  %3 = load void (i32)*, void (i32)** %2, align 4, !dbg !1100, !tbaa !112
  tail call void %3(i32 %0) #11, !dbg !1101
  unreachable, !dbg !1102
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @env___box_flush(i32) #4 !dbg !804 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !803, metadata !DIExpression()), !dbg !1103
  %2 = load i32*, i32** @__box_importjumptable, align 4, !dbg !1104, !tbaa !91
  %3 = getelementptr inbounds i32, i32* %2, i32 2, !dbg !1104
  %4 = bitcast i32* %3 to i32 (i32)**, !dbg !1104
  %5 = load i32 (i32)*, i32 (i32)** %4, align 4, !dbg !1104, !tbaa !112
  %6 = tail call i32 %5(i32 %0) #11, !dbg !1105
  ret i32 %6, !dbg !1106
}

; Function Attrs: minsize nounwind optsize
define weak dso_local void @populate_table() local_unnamed_addr #4 !dbg !1107 {
  ret void, !dbg !1108
}

; Function Attrs: minsize nounwind optsize
define weak dso_local void @populate_globals() local_unnamed_addr #4 !dbg !1109 {
  ret void, !dbg !1110
}

; Function Attrs: minsize nounwind optsize
define weak dso_local void @populate_memory() local_unnamed_addr #4 !dbg !1111 {
  ret void, !dbg !1112
}

; Function Attrs: minsize nounwind optsize
define weak dso_local void @wasmf___wasm_call_ctors() local_unnamed_addr #4 !dbg !1113 {
  ret void, !dbg !1114
}

; Function Attrs: minsize nofree norecurse nounwind optsize
define dso_local i8* @__box_push(i32) #0 !dbg !1115 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !1119, metadata !DIExpression()), !dbg !1121
  %2 = load i8*, i8** @__box_datasp, align 4, !dbg !1122, !tbaa !91
  call void @llvm.dbg.value(metadata i8* %2, metadata !1120, metadata !DIExpression()), !dbg !1121
  %3 = getelementptr inbounds i8, i8* %2, i32 %0, !dbg !1123
  %4 = icmp ugt i8* %3, @__memory_end, !dbg !1125
  br i1 %4, label %6, label %5, !dbg !1126

5:                                                ; preds = %1
  store i8* %3, i8** @__box_datasp, align 4, !dbg !1127, !tbaa !91
  br label %6, !dbg !1128

6:                                                ; preds = %5, %1
  %7 = phi i8* [ %3, %5 ], [ null, %1 ], !dbg !1121
  ret i8* %7, !dbg !1129
}

; Function Attrs: minsize nounwind optsize
define dso_local void @__box_pop(i32) #4 !dbg !1130 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !1134, metadata !DIExpression()), !dbg !1135
  %2 = load i8*, i8** @__box_datasp, align 4, !dbg !1136, !tbaa !91
  %3 = sub i32 0, %0, !dbg !1138
  %4 = getelementptr inbounds i8, i8* %2, i32 %3, !dbg !1138
  %5 = icmp ult i8* %4, @__memory_start, !dbg !1139
  br i1 %5, label %6, label %9, !dbg !1140, !prof !1020

6:                                                ; preds = %1
  call void @llvm.dbg.value(metadata i32 -14, metadata !104, metadata !DIExpression()) #5, !dbg !1141
  %7 = load void (i32)**, void (i32)*** bitcast (i32** @__box_importjumptable to void (i32)***), align 4, !dbg !1144, !tbaa !91
  %8 = load void (i32)*, void (i32)** %7, align 4, !dbg !1144, !tbaa !112
  tail call void %8(i32 -14) #11, !dbg !1145
  unreachable, !dbg !1146

9:                                                ; preds = %1
  store i8* %4, i8** @__box_datasp, align 4, !dbg !1147, !tbaa !91
  ret void, !dbg !1148
}

; Function Attrs: minsize nounwind optsize
define dso_local i32 @__box_init(i32*) #4 !dbg !1149 {
  call void @llvm.dbg.value(metadata i32* %0, metadata !1153, metadata !DIExpression()), !dbg !1160
  call void @llvm.dbg.value(metadata i32* @__data_init_start, metadata !1154, metadata !DIExpression()), !dbg !1160
  call void @llvm.dbg.value(metadata i32* @__data_start, metadata !1155, metadata !DIExpression()), !dbg !1161
  br label %2, !dbg !1162

2:                                                ; preds = %6, %1
  %3 = phi i32* [ @__data_init_start, %1 ], [ %7, %6 ], !dbg !1160
  %4 = phi i32* [ @__data_start, %1 ], [ %9, %6 ], !dbg !1161
  call void @llvm.dbg.value(metadata i32* %4, metadata !1155, metadata !DIExpression()), !dbg !1161
  call void @llvm.dbg.value(metadata i32* %3, metadata !1154, metadata !DIExpression()), !dbg !1160
  %5 = icmp ult i32* %4, @__data_end, !dbg !1163
  br i1 %5, label %6, label %10, !dbg !1165

6:                                                ; preds = %2
  %7 = getelementptr inbounds i32, i32* %3, i32 1, !dbg !1166
  call void @llvm.dbg.value(metadata i32* %7, metadata !1154, metadata !DIExpression()), !dbg !1160
  %8 = load i32, i32* %3, align 4, !dbg !1168, !tbaa !112
  store i32 %8, i32* %4, align 4, !dbg !1169, !tbaa !112
  %9 = getelementptr inbounds i32, i32* %4, i32 1, !dbg !1170
  call void @llvm.dbg.value(metadata i32* %9, metadata !1155, metadata !DIExpression()), !dbg !1161
  br label %2, !dbg !1171, !llvm.loop !1172

10:                                               ; preds = %14, %2
  %11 = phi i32* [ %15, %14 ], [ @__bss_start, %2 ], !dbg !1174
  call void @llvm.dbg.value(metadata i32* %11, metadata !1158, metadata !DIExpression()), !dbg !1174
  %12 = icmp ult i32* %11, @__bss_end, !dbg !1175
  br i1 %12, label %14, label %13, !dbg !1177

13:                                               ; preds = %10
  store i32* %0, i32** @__box_importjumptable, align 4, !dbg !1178, !tbaa !91
  tail call void @__libc_init_array() #11, !dbg !1179
  tail call void @populate_table() #12, !dbg !1180
  tail call void @populate_globals() #12, !dbg !1181
  tail call void @populate_memory() #12, !dbg !1182
  tail call void @wasmf___wasm_call_ctors() #12, !dbg !1183
  ret i32 0, !dbg !1184

14:                                               ; preds = %10
  store i32 0, i32* %11, align 4, !dbg !1185, !tbaa !112
  %15 = getelementptr inbounds i32, i32* %11, i32 1, !dbg !1187
  call void @llvm.dbg.value(metadata i32* %15, metadata !1158, metadata !DIExpression()), !dbg !1174
  br label %10, !dbg !1188, !llvm.loop !1189
}

; Function Attrs: minsize optsize
declare dso_local void @__libc_init_array() local_unnamed_addr #3

; Function Attrs: minsize nounwind optsize
define dso_local i32 @env___box_write(i32, i32, i32) #4 !dbg !517 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !516, metadata !DIExpression()), !dbg !1191
  call void @llvm.dbg.value(metadata i32 %1, metadata !521, metadata !DIExpression()), !dbg !1191
  call void @llvm.dbg.value(metadata i32 %2, metadata !522, metadata !DIExpression()), !dbg !1191
  %4 = load i32*, i32** @__box_importjumptable, align 4, !dbg !1192, !tbaa !91
  %5 = getelementptr inbounds i32, i32* %4, i32 1, !dbg !1192
  %6 = bitcast i32* %5 to i32 (i32, i8*, i32)**, !dbg !1192
  %7 = load i32 (i32, i8*, i32)*, i32 (i32, i8*, i32)** %6, align 4, !dbg !1192, !tbaa !112
  call void @llvm.dbg.value(metadata i32 %1, metadata !526, metadata !DIExpression()), !dbg !1193
  %8 = getelementptr inbounds [0 x i8], [0 x i8]* @__memory, i32 0, i32 %1, !dbg !1195
  %9 = tail call i32 %7(i32 %0, i8* nonnull %8, i32 %2) #11, !dbg !1196
  ret i32 %9, !dbg !1197
}

; Function Attrs: minsize optsize
declare dso_local i32 @wasmf_mandlebrot(i32, i32, i32) #3

; Function Attrs: nounwind readnone speculatable
declare void @llvm.dbg.value(metadata, metadata, metadata) #10

attributes #0 = { minsize nofree norecurse nounwind optsize "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #1 = { argmemonly nounwind }
attributes #2 = { minsize noreturn nounwind optsize "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #3 = { minsize optsize "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #4 = { minsize nounwind optsize "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #5 = { nounwind }
attributes #6 = { alwaysinline minsize norecurse nounwind optsize readnone "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #7 = { alwaysinline minsize norecurse nounwind optsize readonly "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #8 = { alwaysinline minsize nofree norecurse nounwind optsize writeonly "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #9 = { alwaysinline minsize nounwind optsize "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "min-legal-vector-width"="0" "no-frame-pointer-elim"="true" "no-frame-pointer-elim-non-leaf" "no-infs-fp-math"="false" "no-jump-tables"="false" "no-nans-fp-math"="false" "no-signed-zeros-fp-math"="false" "no-trapping-math"="false" "stack-protector-buffer-size"="8" "target-cpu"="cortex-m4" "target-features"="+armv7e-m,+dsp,+fp16,+fpregs,+hwdiv,+strict-align,+thumb-mode,+vfp2d16sp,+vfp3d16sp,+vfp4d16sp,-aes,-crc,-crypto,-d32,-dotprod,-fp-armv8,-fp-armv8d16,-fp-armv8d16sp,-fp-armv8sp,-fp16fml,-fp64,-fullfp16,-hwdiv-arm,-lob,-mve,-mve.fp,-neon,-ras,-sb,-sha2,-vfp2,-vfp2d16,-vfp2sp,-vfp3,-vfp3d16,-vfp3sp,-vfp4,-vfp4d16,-vfp4sp" "unsafe-fp-math"="false" "use-soft-float"="false" }
attributes #10 = { nounwind readnone speculatable }
attributes #11 = { minsize nobuiltin nounwind optsize }
attributes #12 = { minsize nobuiltin optsize }

!llvm.dbg.cu = !{!2}
!llvm.module.flags = !{!74, !75, !76, !77, !78, !79}
!llvm.ident = !{!80}

!0 = !DIGlobalVariableExpression(var: !1, expr: !DIExpression())
!1 = distinct !DIGlobalVariable(name: "__heap_brk", scope: !2, file: !3, line: 116, type: !29, isLocal: true, isDefinition: true)
!2 = distinct !DICompileUnit(language: DW_LANG_C99, file: !3, producer: "clang version 9.0.0-2 (tags/RELEASE_900/final)", isOptimized: true, runtimeVersion: 0, emissionKind: FullDebug, enums: !4, retainedTypes: !5, globals: !60, nameTableKind: None)
!3 = !DIFile(filename: "runtime/bb.c", directory: "/home/geky/bb/bento/examples/awsm-mandlebrot/mandlebrot")
!4 = !{}
!5 = !{!6, !7, !12, !17, !20, !22, !24, !29, !30, !34, !38, !39, !43, !45, !47, !50, !57}
!6 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: null, size: 32)
!7 = !DIDerivedType(tag: DW_TAG_typedef, name: "uint32_t", file: !8, line: 48, baseType: !9)
!8 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/sys/_stdint.h", directory: "")
!9 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uint32_t", file: !10, line: 79, baseType: !11)
!10 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/machine/_default_types.h", directory: "")
!11 = !DIBasicType(name: "unsigned int", size: 32, encoding: DW_ATE_unsigned)
!12 = !DIDerivedType(tag: DW_TAG_typedef, name: "ssize_t", file: !13, line: 200, baseType: !14)
!13 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/sys/types.h", directory: "")
!14 = !DIDerivedType(tag: DW_TAG_typedef, name: "_ssize_t", file: !15, line: 145, baseType: !16)
!15 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/sys/_types.h", directory: "")
!16 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)
!17 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !18, size: 32)
!18 = !DIDerivedType(tag: DW_TAG_const_type, baseType: !19)
!19 = !DIBasicType(name: "char", size: 8, encoding: DW_ATE_unsigned_char)
!20 = !DIDerivedType(tag: DW_TAG_typedef, name: "uintptr_t", file: !8, line: 82, baseType: !21)
!21 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uintptr_t", file: !10, line: 232, baseType: !11)
!22 = !DIDerivedType(tag: DW_TAG_typedef, name: "int32_t", file: !8, line: 44, baseType: !23)
!23 = !DIDerivedType(tag: DW_TAG_typedef, name: "__int32_t", file: !10, line: 77, baseType: !16)
!24 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !25, size: 32)
!25 = !DIDerivedType(tag: DW_TAG_const_type, baseType: !26)
!26 = !DIDerivedType(tag: DW_TAG_typedef, name: "uint8_t", file: !8, line: 24, baseType: !27)
!27 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uint8_t", file: !10, line: 43, baseType: !28)
!28 = !DIBasicType(name: "unsigned char", size: 8, encoding: DW_ATE_unsigned_char)
!29 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !26, size: 32)
!30 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !31, size: 32)
!31 = !DIDerivedType(tag: DW_TAG_typedef, name: "int8_t", file: !8, line: 20, baseType: !32)
!32 = !DIDerivedType(tag: DW_TAG_typedef, name: "__int8_t", file: !10, line: 41, baseType: !33)
!33 = !DIBasicType(name: "signed char", size: 8, encoding: DW_ATE_signed_char)
!34 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !35, size: 32)
!35 = !DIDerivedType(tag: DW_TAG_typedef, name: "int16_t", file: !8, line: 32, baseType: !36)
!36 = !DIDerivedType(tag: DW_TAG_typedef, name: "__int16_t", file: !10, line: 55, baseType: !37)
!37 = !DIBasicType(name: "short", size: 16, encoding: DW_ATE_signed)
!38 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !22, size: 32)
!39 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !40, size: 32)
!40 = !DIDerivedType(tag: DW_TAG_typedef, name: "int64_t", file: !8, line: 56, baseType: !41)
!41 = !DIDerivedType(tag: DW_TAG_typedef, name: "__int64_t", file: !10, line: 103, baseType: !42)
!42 = !DIBasicType(name: "long long int", size: 64, encoding: DW_ATE_signed)
!43 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !44, size: 32)
!44 = !DIBasicType(name: "float", size: 32, encoding: DW_ATE_float)
!45 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !46, size: 32)
!46 = !DIBasicType(name: "double", size: 64, encoding: DW_ATE_float)
!47 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !48, size: 32)
!48 = !DISubroutineType(types: !49)
!49 = !{null, !16}
!50 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !51, size: 32)
!51 = !DISubroutineType(types: !52)
!52 = !{!12, !22, !53, !55}
!53 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !54, size: 32)
!54 = !DIDerivedType(tag: DW_TAG_const_type, baseType: null)
!55 = !DIDerivedType(tag: DW_TAG_typedef, name: "size_t", file: !56, line: 46, baseType: !11)
!56 = !DIFile(filename: "/usr/lib/llvm-9/lib/clang/9.0.0/include/stddef.h", directory: "")
!57 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !58, size: 32)
!58 = !DISubroutineType(types: !59)
!59 = !{!16, !22}
!60 = !{!61, !64, !66, !71, !0}
!61 = !DIGlobalVariableExpression(var: !62, expr: !DIExpression())
!62 = distinct !DIGlobalVariable(name: "memory_size", scope: !2, file: !3, line: 537, type: !63, isLocal: false, isDefinition: true)
!63 = !DIDerivedType(tag: DW_TAG_const_type, baseType: !7)
!64 = !DIGlobalVariableExpression(var: !65, expr: !DIExpression())
!65 = distinct !DIGlobalVariable(name: "__box_datasp", scope: !2, file: !3, line: 604, type: !29, isLocal: false, isDefinition: true)
!66 = !DIGlobalVariableExpression(var: !67, expr: !DIExpression())
!67 = distinct !DIGlobalVariable(name: "__box_exportjumptable", scope: !2, file: !3, line: 688, type: !68, isLocal: false, isDefinition: true)
!68 = !DICompositeType(tag: DW_TAG_array_type, baseType: !63, size: 128, elements: !69)
!69 = !{!70}
!70 = !DISubrange(count: 4)
!71 = !DIGlobalVariableExpression(var: !72, expr: !DIExpression())
!72 = distinct !DIGlobalVariable(name: "__box_importjumptable", scope: !2, file: !3, line: 626, type: !73, isLocal: false, isDefinition: true)
!73 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !63, size: 32)
!74 = !{i32 2, !"Dwarf Version", i32 4}
!75 = !{i32 2, !"Debug Info Version", i32 3}
!76 = !{i32 1, !"wchar_size", i32 4}
!77 = !{i32 1, !"min_enum_size", i32 1}
!78 = !{i32 1, !"ThinLTO", i32 0}
!79 = !{i32 1, !"EnableSplitLTOUnit", i32 0}
!80 = !{!"clang version 9.0.0-2 (tags/RELEASE_900/final)"}
!81 = distinct !DISubprogram(name: "_sbrk", scope: !3, file: !3, line: 123, type: !82, scopeLine: 123, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !85)
!82 = !DISubroutineType(types: !83)
!83 = !{!6, !84}
!84 = !DIDerivedType(tag: DW_TAG_typedef, name: "ptrdiff_t", file: !56, line: 35, baseType: !16)
!85 = !{!86, !87}
!86 = !DILocalVariable(name: "diff", arg: 1, scope: !81, file: !3, line: 123, type: !84)
!87 = !DILocalVariable(name: "pbrk", scope: !81, file: !3, line: 128, type: !29)
!88 = !DILocation(line: 0, scope: !81)
!89 = !DILocation(line: 124, column: 10, scope: !90)
!90 = distinct !DILexicalBlock(scope: !81, file: !3, line: 124, column: 9)
!91 = !{!92, !92, i64 0}
!92 = !{!"any pointer", !93, i64 0}
!93 = !{!"omnipotent char", !94, i64 0}
!94 = !{!"Simple C/C++ TBAA"}
!95 = !DILocation(line: 124, column: 9, scope: !81)
!96 = !DILocation(line: 129, column: 14, scope: !97)
!97 = distinct !DILexicalBlock(scope: !81, file: !3, line: 129, column: 9)
!98 = !DILocation(line: 129, column: 21, scope: !97)
!99 = !DILocation(line: 129, column: 9, scope: !81)
!100 = !DILocation(line: 135, column: 1, scope: !81)
!101 = distinct !DISubprogram(name: "__wrap_abort", scope: !3, file: !3, line: 142, type: !102, scopeLine: 142, flags: DIFlagPrototyped | DIFlagNoReturn, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!102 = !DISubroutineType(types: !103)
!103 = !{null}
!104 = !DILocalVariable(name: "a0", arg: 1, scope: !105, file: !3, line: 664, type: !22)
!105 = distinct !DISubprogram(name: "env___box_abort", scope: !3, file: !3, line: 664, type: !106, scopeLine: 664, flags: DIFlagPrototyped | DIFlagNoReturn, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !108)
!106 = !DISubroutineType(types: !107)
!107 = !{null, !22}
!108 = !{!104}
!109 = !DILocation(line: 0, scope: !105, inlinedAt: !110)
!110 = distinct !DILocation(line: 143, column: 5, scope: !101)
!111 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !110)
!112 = !{!113, !113, i64 0}
!113 = !{!"int", !93, i64 0}
!114 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !110)
!115 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !110)
!116 = distinct !DISubprogram(name: "__wrap_exit", scope: !3, file: !3, line: 147, type: !48, scopeLine: 147, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !117)
!117 = !{!118}
!118 = !DILocalVariable(name: "code", arg: 1, scope: !116, file: !3, line: 147, type: !16)
!119 = !DILocation(line: 0, scope: !116)
!120 = !DILocation(line: 148, column: 22, scope: !116)
!121 = !DILocation(line: 148, column: 17, scope: !116)
!122 = !DILocation(line: 0, scope: !105, inlinedAt: !123)
!123 = distinct !DILocation(line: 148, column: 5, scope: !116)
!124 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !123)
!125 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !123)
!126 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !123)
!127 = distinct !DISubprogram(name: "__assert_func", scope: !3, file: !3, line: 153, type: !128, scopeLine: 154, flags: DIFlagPrototyped | DIFlagNoReturn, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !130)
!128 = !DISubroutineType(types: !129)
!129 = !{null, !17, !16, !17, !17}
!130 = !{!131, !132, !133, !134}
!131 = !DILocalVariable(name: "file", arg: 1, scope: !127, file: !3, line: 153, type: !17)
!132 = !DILocalVariable(name: "line", arg: 2, scope: !127, file: !3, line: 153, type: !16)
!133 = !DILocalVariable(name: "func", arg: 3, scope: !127, file: !3, line: 154, type: !17)
!134 = !DILocalVariable(name: "expr", arg: 4, scope: !127, file: !3, line: 154, type: !17)
!135 = !DILocation(line: 0, scope: !127)
!136 = !DILocation(line: 155, column: 5, scope: !127)
!137 = !DILocation(line: 0, scope: !105, inlinedAt: !138)
!138 = distinct !DILocation(line: 156, column: 5, scope: !127)
!139 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !138)
!140 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !138)
!141 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !138)
!142 = distinct !DISubprogram(name: "_exit", scope: !3, file: !3, line: 160, type: !48, scopeLine: 160, flags: DIFlagPrototyped | DIFlagNoReturn, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !143)
!143 = !{!144}
!144 = !DILocalVariable(name: "code", arg: 1, scope: !142, file: !3, line: 160, type: !16)
!145 = !DILocation(line: 0, scope: !142)
!146 = !DILocation(line: 161, column: 22, scope: !142)
!147 = !DILocation(line: 161, column: 17, scope: !142)
!148 = !DILocation(line: 0, scope: !105, inlinedAt: !149)
!149 = distinct !DILocation(line: 161, column: 5, scope: !142)
!150 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !149)
!151 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !149)
!152 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !149)
!153 = distinct !DISubprogram(name: "__box_cbprintf", scope: !3, file: !3, line: 167, type: !154, scopeLine: 169, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !165)
!154 = !DISubroutineType(types: !155)
!155 = !{!12, !156, !6, !17, !159}
!156 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !157, size: 32)
!157 = !DISubroutineType(types: !158)
!158 = !{!12, !6, !53, !55}
!159 = !DIDerivedType(tag: DW_TAG_typedef, name: "va_list", file: !160, line: 14, baseType: !161)
!160 = !DIFile(filename: "/usr/lib/llvm-9/lib/clang/9.0.0/include/stdarg.h", directory: "")
!161 = !DIDerivedType(tag: DW_TAG_typedef, name: "__builtin_va_list", file: !3, line: 162, baseType: !162)
!162 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "__va_list", file: !3, line: 162, size: 32, elements: !163)
!163 = !{!164}
!164 = !DIDerivedType(tag: DW_TAG_member, name: "__ap", scope: !162, file: !3, line: 162, baseType: !6, size: 32)
!165 = !{!166, !167, !168, !169, !170, !171, !172, !174, !177, !179, !180, !181, !182, !183, !184, !185, !186, !198, !201, !203, !207, !211, !215, !218, !219, !222, !225, !229, !232, !233, !234, !237, !240, !244, !246, !247, !248, !249, !253, !256}
!166 = !DILocalVariable(name: "write", arg: 1, scope: !153, file: !3, line: 168, type: !156)
!167 = !DILocalVariable(name: "ctx", arg: 2, scope: !153, file: !3, line: 168, type: !6)
!168 = !DILocalVariable(name: "format", arg: 3, scope: !153, file: !3, line: 169, type: !17)
!169 = !DILocalVariable(name: "args", arg: 4, scope: !153, file: !3, line: 169, type: !159)
!170 = !DILocalVariable(name: "p", scope: !153, file: !3, line: 170, type: !17)
!171 = !DILocalVariable(name: "res", scope: !153, file: !3, line: 171, type: !12)
!172 = !DILocalVariable(name: "skip", scope: !173, file: !3, line: 174, type: !55)
!173 = distinct !DILexicalBlock(scope: !153, file: !3, line: 172, column: 18)
!174 = !DILocalVariable(name: "nres", scope: !175, file: !3, line: 176, type: !12)
!175 = distinct !DILexicalBlock(scope: !176, file: !3, line: 175, column: 23)
!176 = distinct !DILexicalBlock(scope: !173, file: !3, line: 175, column: 13)
!177 = !DILocalVariable(name: "zero_justify", scope: !173, file: !3, line: 191, type: !178)
!178 = !DIBasicType(name: "_Bool", size: 8, encoding: DW_ATE_boolean)
!179 = !DILocalVariable(name: "left_justify", scope: !173, file: !3, line: 192, type: !178)
!180 = !DILocalVariable(name: "precision_mode", scope: !173, file: !3, line: 193, type: !178)
!181 = !DILocalVariable(name: "width", scope: !173, file: !3, line: 194, type: !55)
!182 = !DILocalVariable(name: "precision", scope: !173, file: !3, line: 195, type: !55)
!183 = !DILocalVariable(name: "mode", scope: !173, file: !3, line: 197, type: !19)
!184 = !DILocalVariable(name: "value", scope: !173, file: !3, line: 198, type: !7)
!185 = !DILocalVariable(name: "size", scope: !173, file: !3, line: 199, type: !55)
!186 = !DILocalVariable(name: "s", scope: !187, file: !3, line: 245, type: !17)
!187 = distinct !DILexicalBlock(scope: !188, file: !3, line: 242, column: 37)
!188 = distinct !DILexicalBlock(scope: !189, file: !3, line: 242, column: 24)
!189 = distinct !DILexicalBlock(scope: !190, file: !3, line: 235, column: 24)
!190 = distinct !DILexicalBlock(scope: !191, file: !3, line: 228, column: 24)
!191 = distinct !DILexicalBlock(scope: !192, file: !3, line: 224, column: 24)
!192 = distinct !DILexicalBlock(scope: !193, file: !3, line: 220, column: 24)
!193 = distinct !DILexicalBlock(scope: !194, file: !3, line: 212, column: 24)
!194 = distinct !DILexicalBlock(scope: !195, file: !3, line: 202, column: 17)
!195 = distinct !DILexicalBlock(scope: !196, file: !3, line: 201, column: 22)
!196 = distinct !DILexicalBlock(scope: !197, file: !3, line: 201, column: 9)
!197 = distinct !DILexicalBlock(scope: !173, file: !3, line: 201, column: 9)
!198 = !DILocalVariable(name: "d", scope: !199, file: !3, line: 257, type: !22)
!199 = distinct !DILexicalBlock(scope: !200, file: !3, line: 254, column: 52)
!200 = distinct !DILexicalBlock(scope: !188, file: !3, line: 254, column: 24)
!201 = !DILocalVariable(name: "t", scope: !202, file: !3, line: 264, type: !7)
!202 = distinct !DILexicalBlock(scope: !199, file: !3, line: 264, column: 17)
!203 = !DILocalVariable(name: "t", scope: !204, file: !3, line: 277, type: !7)
!204 = distinct !DILexicalBlock(scope: !205, file: !3, line: 277, column: 17)
!205 = distinct !DILexicalBlock(scope: !206, file: !3, line: 272, column: 37)
!206 = distinct !DILexicalBlock(scope: !200, file: !3, line: 272, column: 24)
!207 = !DILocalVariable(name: "t", scope: !208, file: !3, line: 301, type: !7)
!208 = distinct !DILexicalBlock(scope: !209, file: !3, line: 301, column: 17)
!209 = distinct !DILexicalBlock(scope: !210, file: !3, line: 288, column: 20)
!210 = distinct !DILexicalBlock(scope: !206, file: !3, line: 285, column: 24)
!211 = !DILocalVariable(name: "i", scope: !212, file: !3, line: 316, type: !12)
!212 = distinct !DILexicalBlock(scope: !213, file: !3, line: 316, column: 13)
!213 = distinct !DILexicalBlock(scope: !214, file: !3, line: 315, column: 28)
!214 = distinct !DILexicalBlock(scope: !173, file: !3, line: 315, column: 13)
!215 = !DILocalVariable(name: "c", scope: !216, file: !3, line: 317, type: !19)
!216 = distinct !DILexicalBlock(scope: !217, file: !3, line: 316, column: 72)
!217 = distinct !DILexicalBlock(scope: !212, file: !3, line: 316, column: 13)
!218 = !DILocalVariable(name: "nres", scope: !216, file: !3, line: 318, type: !12)
!219 = !DILocalVariable(name: "nres", scope: !220, file: !3, line: 327, type: !12)
!220 = distinct !DILexicalBlock(scope: !221, file: !3, line: 326, column: 26)
!221 = distinct !DILexicalBlock(scope: !173, file: !3, line: 326, column: 13)
!222 = !DILocalVariable(name: "nres", scope: !223, file: !3, line: 333, type: !12)
!223 = distinct !DILexicalBlock(scope: !224, file: !3, line: 332, column: 33)
!224 = distinct !DILexicalBlock(scope: !221, file: !3, line: 332, column: 20)
!225 = !DILocalVariable(name: "i", scope: !226, file: !3, line: 339, type: !12)
!226 = distinct !DILexicalBlock(scope: !227, file: !3, line: 339, column: 13)
!227 = distinct !DILexicalBlock(scope: !228, file: !3, line: 338, column: 33)
!228 = distinct !DILexicalBlock(scope: !224, file: !3, line: 338, column: 20)
!229 = !DILocalVariable(name: "digit", scope: !230, file: !3, line: 340, type: !7)
!230 = distinct !DILexicalBlock(scope: !231, file: !3, line: 339, column: 51)
!231 = distinct !DILexicalBlock(scope: !226, file: !3, line: 339, column: 13)
!232 = !DILocalVariable(name: "c", scope: !230, file: !3, line: 342, type: !19)
!233 = !DILocalVariable(name: "nres", scope: !230, file: !3, line: 343, type: !12)
!234 = !DILocalVariable(name: "i", scope: !235, file: !3, line: 350, type: !12)
!235 = distinct !DILexicalBlock(scope: !236, file: !3, line: 349, column: 48)
!236 = distinct !DILexicalBlock(scope: !228, file: !3, line: 349, column: 20)
!237 = !DILocalVariable(name: "nres", scope: !238, file: !3, line: 353, type: !12)
!238 = distinct !DILexicalBlock(scope: !239, file: !3, line: 352, column: 52)
!239 = distinct !DILexicalBlock(scope: !235, file: !3, line: 352, column: 17)
!240 = !DILocalVariable(name: "temp", scope: !241, file: !3, line: 364, type: !7)
!241 = distinct !DILexicalBlock(scope: !242, file: !3, line: 363, column: 33)
!242 = distinct !DILexicalBlock(scope: !243, file: !3, line: 363, column: 13)
!243 = distinct !DILexicalBlock(scope: !235, file: !3, line: 363, column: 13)
!244 = !DILocalVariable(name: "j", scope: !245, file: !3, line: 365, type: !16)
!245 = distinct !DILexicalBlock(scope: !241, file: !3, line: 365, column: 17)
!246 = !DILocalVariable(name: "digit", scope: !241, file: !3, line: 368, type: !7)
!247 = !DILocalVariable(name: "c", scope: !241, file: !3, line: 370, type: !19)
!248 = !DILocalVariable(name: "nres", scope: !241, file: !3, line: 371, type: !12)
!249 = !DILocalVariable(name: "i", scope: !250, file: !3, line: 380, type: !12)
!250 = distinct !DILexicalBlock(scope: !251, file: !3, line: 380, column: 13)
!251 = distinct !DILexicalBlock(scope: !252, file: !3, line: 379, column: 27)
!252 = distinct !DILexicalBlock(scope: !173, file: !3, line: 379, column: 13)
!253 = !DILocalVariable(name: "c", scope: !254, file: !3, line: 381, type: !19)
!254 = distinct !DILexicalBlock(scope: !255, file: !3, line: 380, column: 72)
!255 = distinct !DILexicalBlock(scope: !250, file: !3, line: 380, column: 13)
!256 = !DILocalVariable(name: "nres", scope: !254, file: !3, line: 382, type: !12)
!257 = !DILocation(line: 0, scope: !153)
!258 = !DILocation(line: 0, scope: !173)
!259 = !DILocation(line: 0, scope: !223)
!260 = !DILocation(line: 172, column: 5, scope: !153)
!261 = !DILocation(line: 171, column: 13, scope: !153)
!262 = !DILocation(line: 174, column: 23, scope: !173)
!263 = !DILocation(line: 175, column: 18, scope: !176)
!264 = !DILocation(line: 175, column: 13, scope: !173)
!265 = !DILocation(line: 176, column: 28, scope: !175)
!266 = !DILocation(line: 0, scope: !175)
!267 = !DILocation(line: 177, column: 22, scope: !268)
!268 = distinct !DILexicalBlock(scope: !175, file: !3, line: 177, column: 17)
!269 = !DILocation(line: 177, column: 17, scope: !175)
!270 = !DILocation(line: 183, column: 11, scope: !173)
!271 = !DILocation(line: 186, column: 14, scope: !272)
!272 = distinct !DILexicalBlock(scope: !173, file: !3, line: 186, column: 13)
!273 = !{!93, !93, i64 0}
!274 = !DILocation(line: 186, column: 13, scope: !173)
!275 = !DILocation(line: 198, column: 9, scope: !173)
!276 = !DILocation(line: 198, column: 18, scope: !173)
!277 = !DILocation(line: 201, column: 9, scope: !173)
!278 = !DILocation(line: 201, column: 9, scope: !197)
!279 = !DILocation(line: 202, column: 17, scope: !194)
!280 = !DILocation(line: 202, column: 29, scope: !194)
!281 = !DILocation(line: 204, column: 21, scope: !282)
!282 = distinct !DILexicalBlock(scope: !194, file: !3, line: 202, column: 45)
!283 = !DILocation(line: 205, column: 42, scope: !284)
!284 = distinct !DILexicalBlock(scope: !285, file: !3, line: 204, column: 37)
!285 = distinct !DILexicalBlock(scope: !282, file: !3, line: 204, column: 21)
!286 = !DILocation(line: 205, column: 53, scope: !284)
!287 = !DILocation(line: 205, column: 46, scope: !284)
!288 = !DILocation(line: 206, column: 17, scope: !284)
!289 = distinct !{!289, !278, !290}
!290 = !DILocation(line: 309, column: 9, scope: !197)
!291 = !DILocation(line: 206, column: 33, scope: !292)
!292 = distinct !DILexicalBlock(scope: !285, file: !3, line: 206, column: 28)
!293 = !DILocation(line: 206, column: 48, scope: !292)
!294 = !DILocation(line: 206, column: 39, scope: !292)
!295 = !DILocation(line: 207, column: 34, scope: !296)
!296 = distinct !DILexicalBlock(scope: !292, file: !3, line: 206, column: 53)
!297 = !DILocation(line: 207, column: 45, scope: !296)
!298 = !DILocation(line: 207, column: 38, scope: !296)
!299 = !DILocation(line: 208, column: 17, scope: !296)
!300 = !DILocation(line: 212, column: 24, scope: !194)
!301 = !DILocation(line: 0, scope: !302)
!302 = distinct !DILexicalBlock(scope: !303, file: !3, line: 214, column: 21)
!303 = distinct !DILexicalBlock(scope: !193, file: !3, line: 212, column: 37)
!304 = !DILocation(line: 231, column: 23, scope: !305)
!305 = distinct !DILexicalBlock(scope: !190, file: !3, line: 228, column: 37)
!306 = !DILocation(line: 233, column: 17, scope: !305)
!307 = !DILocation(line: 238, column: 25, scope: !308)
!308 = distinct !DILexicalBlock(scope: !189, file: !3, line: 235, column: 37)
!309 = !DILocation(line: 238, column: 23, scope: !308)
!310 = !DILocation(line: 240, column: 17, scope: !308)
!311 = !DILocation(line: 245, column: 33, scope: !187)
!312 = !DILocation(line: 0, scope: !187)
!313 = !DILocation(line: 246, column: 25, scope: !187)
!314 = !DILocation(line: 246, column: 23, scope: !187)
!315 = !DILocation(line: 249, column: 17, scope: !187)
!316 = !DILocation(line: 249, column: 24, scope: !187)
!317 = !DILocation(line: 249, column: 51, scope: !187)
!318 = !DILocation(line: 249, column: 32, scope: !187)
!319 = !DILocation(line: 250, column: 26, scope: !320)
!320 = distinct !DILexicalBlock(scope: !187, file: !3, line: 249, column: 73)
!321 = distinct !{!321, !315, !322}
!322 = !DILocation(line: 251, column: 17, scope: !187)
!323 = !DILocation(line: 257, column: 29, scope: !199)
!324 = !DILocation(line: 0, scope: !199)
!325 = !DILocation(line: 258, column: 23, scope: !199)
!326 = !DILocation(line: 260, column: 23, scope: !327)
!327 = distinct !DILexicalBlock(scope: !199, file: !3, line: 260, column: 21)
!328 = !DILocation(line: 262, column: 25, scope: !329)
!329 = distinct !DILexicalBlock(scope: !327, file: !3, line: 260, column: 28)
!330 = !DILocation(line: 260, column: 21, scope: !199)
!331 = !DILocation(line: 0, scope: !202)
!332 = !DILocation(line: 264, column: 22, scope: !202)
!333 = !DILocation(line: 264, column: 40, scope: !334)
!334 = distinct !DILexicalBlock(scope: !202, file: !3, line: 264, column: 17)
!335 = !DILocation(line: 264, column: 17, scope: !202)
!336 = !DILocation(line: 267, column: 26, scope: !337)
!337 = distinct !DILexicalBlock(scope: !199, file: !3, line: 267, column: 21)
!338 = !DILocation(line: 267, column: 21, scope: !199)
!339 = !DILocation(line: 265, column: 26, scope: !340)
!340 = distinct !DILexicalBlock(scope: !334, file: !3, line: 264, column: 54)
!341 = !DILocation(line: 264, column: 47, scope: !334)
!342 = !DILocation(line: 264, column: 17, scope: !334)
!343 = distinct !{!343, !335, !344}
!344 = !DILocation(line: 266, column: 17, scope: !202)
!345 = !DILocation(line: 275, column: 25, scope: !205)
!346 = !DILocation(line: 275, column: 23, scope: !205)
!347 = !DILocation(line: 0, scope: !204)
!348 = !DILocation(line: 277, column: 22, scope: !204)
!349 = !DILocation(line: 0, scope: !205)
!350 = !DILocation(line: 277, column: 44, scope: !351)
!351 = distinct !DILexicalBlock(scope: !204, file: !3, line: 277, column: 17)
!352 = !DILocation(line: 277, column: 17, scope: !204)
!353 = !DILocation(line: 280, column: 26, scope: !354)
!354 = distinct !DILexicalBlock(scope: !205, file: !3, line: 280, column: 21)
!355 = !DILocation(line: 280, column: 21, scope: !205)
!356 = !DILocation(line: 278, column: 26, scope: !357)
!357 = distinct !DILexicalBlock(scope: !351, file: !3, line: 277, column: 58)
!358 = !DILocation(line: 277, column: 51, scope: !351)
!359 = !DILocation(line: 277, column: 17, scope: !351)
!360 = distinct !{!360, !352, !361}
!361 = !DILocation(line: 279, column: 17, scope: !204)
!362 = !DILocation(line: 285, column: 36, scope: !210)
!363 = !DILocation(line: 292, column: 35, scope: !364)
!364 = distinct !DILexicalBlock(scope: !209, file: !3, line: 292, column: 21)
!365 = !DILocation(line: 295, column: 17, scope: !366)
!366 = distinct !DILexicalBlock(scope: !364, file: !3, line: 292, column: 52)
!367 = !DILocation(line: 299, column: 25, scope: !209)
!368 = !DILocation(line: 299, column: 23, scope: !209)
!369 = !DILocation(line: 0, scope: !208)
!370 = !DILocation(line: 301, column: 22, scope: !208)
!371 = !DILocation(line: 0, scope: !209)
!372 = !DILocation(line: 301, column: 44, scope: !373)
!373 = distinct !DILexicalBlock(scope: !208, file: !3, line: 301, column: 17)
!374 = !DILocation(line: 301, column: 17, scope: !208)
!375 = !DILocation(line: 304, column: 26, scope: !376)
!376 = distinct !DILexicalBlock(scope: !209, file: !3, line: 304, column: 21)
!377 = !DILocation(line: 304, column: 21, scope: !209)
!378 = !DILocation(line: 302, column: 26, scope: !379)
!379 = distinct !DILexicalBlock(scope: !373, file: !3, line: 301, column: 58)
!380 = !DILocation(line: 301, column: 51, scope: !373)
!381 = !DILocation(line: 301, column: 17, scope: !373)
!382 = distinct !{!382, !374, !383}
!383 = !DILocation(line: 303, column: 17, scope: !208)
!384 = !DILocation(line: 312, column: 11, scope: !173)
!385 = !DILocation(line: 0, scope: !190)
!386 = !DILocation(line: 194, column: 16, scope: !173)
!387 = !DILocation(line: 315, column: 13, scope: !173)
!388 = !DILocation(line: 0, scope: !217)
!389 = !DILocation(line: 0, scope: !216)
!390 = !DILocation(line: 316, column: 13, scope: !212)
!391 = !DILocation(line: 0, scope: !212)
!392 = !DILocation(line: 316, column: 35, scope: !217)
!393 = !DILocation(line: 317, column: 17, scope: !216)
!394 = !DILocation(line: 317, column: 22, scope: !216)
!395 = !DILocation(line: 318, column: 32, scope: !216)
!396 = !DILocation(line: 319, column: 26, scope: !397)
!397 = distinct !DILexicalBlock(scope: !216, file: !3, line: 319, column: 21)
!398 = !DILocation(line: 319, column: 21, scope: !216)
!399 = !DILocation(line: 323, column: 13, scope: !217)
!400 = !DILocation(line: 316, column: 68, scope: !217)
!401 = !DILocation(line: 316, column: 13, scope: !217)
!402 = distinct !{!402, !390, !403}
!403 = !DILocation(line: 323, column: 13, scope: !212)
!404 = !DILocation(line: 326, column: 13, scope: !173)
!405 = !DILocation(line: 327, column: 28, scope: !220)
!406 = !DILocation(line: 0, scope: !220)
!407 = !DILocation(line: 328, column: 22, scope: !408)
!408 = distinct !DILexicalBlock(scope: !220, file: !3, line: 328, column: 17)
!409 = !DILocation(line: 328, column: 17, scope: !220)
!410 = !DILocation(line: 333, column: 63, scope: !223)
!411 = !DILocation(line: 333, column: 28, scope: !223)
!412 = !DILocation(line: 334, column: 22, scope: !413)
!413 = distinct !DILexicalBlock(scope: !223, file: !3, line: 334, column: 17)
!414 = !DILocation(line: 334, column: 17, scope: !223)
!415 = !DILocation(line: 0, scope: !226)
!416 = !DILocation(line: 339, column: 40, scope: !231)
!417 = !DILocation(line: 339, column: 13, scope: !226)
!418 = !DILocation(line: 340, column: 35, scope: !230)
!419 = !DILocation(line: 340, column: 46, scope: !230)
!420 = !DILocation(line: 340, column: 41, scope: !230)
!421 = !DILocation(line: 340, column: 51, scope: !230)
!422 = !DILocation(line: 0, scope: !230)
!423 = !DILocation(line: 342, column: 17, scope: !230)
!424 = !DILocation(line: 342, column: 34, scope: !230)
!425 = !DILocation(line: 342, column: 27, scope: !230)
!426 = !DILocation(line: 342, column: 59, scope: !230)
!427 = !DILocation(line: 342, column: 26, scope: !230)
!428 = !DILocation(line: 342, column: 22, scope: !230)
!429 = !DILocation(line: 343, column: 32, scope: !230)
!430 = !DILocation(line: 344, column: 26, scope: !431)
!431 = distinct !DILexicalBlock(scope: !230, file: !3, line: 344, column: 21)
!432 = !DILocation(line: 344, column: 21, scope: !230)
!433 = !DILocation(line: 348, column: 13, scope: !231)
!434 = distinct !{!434, !417, !435}
!435 = !DILocation(line: 348, column: 13, scope: !226)
!436 = !DILocation(line: 349, column: 25, scope: !236)
!437 = !DILocation(line: 350, column: 29, scope: !235)
!438 = !DILocation(line: 0, scope: !235)
!439 = !DILocation(line: 352, column: 41, scope: !239)
!440 = !DILocation(line: 352, column: 47, scope: !239)
!441 = !DILocation(line: 352, column: 29, scope: !239)
!442 = !DILocation(line: 353, column: 32, scope: !238)
!443 = !DILocation(line: 0, scope: !238)
!444 = !DILocation(line: 354, column: 26, scope: !445)
!445 = distinct !DILexicalBlock(scope: !238, file: !3, line: 354, column: 21)
!446 = !DILocation(line: 354, column: 21, scope: !238)
!447 = !DILocation(line: 357, column: 21, scope: !238)
!448 = !DILocation(line: 359, column: 26, scope: !238)
!449 = !DILocation(line: 359, column: 25, scope: !238)
!450 = !DILocation(line: 359, column: 23, scope: !238)
!451 = !DILocation(line: 360, column: 19, scope: !238)
!452 = !DILocation(line: 363, column: 13, scope: !243)
!453 = !DILocation(line: 363, column: 22, scope: !242)
!454 = !DILocation(line: 364, column: 33, scope: !241)
!455 = !DILocation(line: 0, scope: !241)
!456 = !DILocation(line: 0, scope: !245)
!457 = !DILocation(line: 365, column: 22, scope: !245)
!458 = !DILocation(line: 365, column: 35, scope: !459)
!459 = distinct !DILexicalBlock(scope: !245, file: !3, line: 365, column: 17)
!460 = !DILocation(line: 365, column: 17, scope: !245)
!461 = !DILocation(line: 368, column: 39, scope: !241)
!462 = !DILocation(line: 370, column: 17, scope: !241)
!463 = !DILocation(line: 370, column: 26, scope: !241)
!464 = !DILocation(line: 370, column: 22, scope: !241)
!465 = !DILocation(line: 371, column: 32, scope: !241)
!466 = !DILocation(line: 372, column: 26, scope: !467)
!467 = distinct !DILexicalBlock(scope: !241, file: !3, line: 372, column: 21)
!468 = !DILocation(line: 372, column: 21, scope: !241)
!469 = !DILocation(line: 376, column: 13, scope: !242)
!470 = !DILocation(line: 366, column: 26, scope: !471)
!471 = distinct !DILexicalBlock(scope: !459, file: !3, line: 365, column: 45)
!472 = !DILocation(line: 365, column: 41, scope: !459)
!473 = !DILocation(line: 365, column: 17, scope: !459)
!474 = distinct !{!474, !460, !475}
!475 = !DILocation(line: 367, column: 17, scope: !245)
!476 = !DILocation(line: 363, column: 29, scope: !242)
!477 = !DILocation(line: 363, column: 13, scope: !242)
!478 = distinct !{!478, !452, !479}
!479 = !DILocation(line: 376, column: 13, scope: !243)
!480 = !DILocation(line: 379, column: 13, scope: !173)
!481 = !DILocation(line: 0, scope: !255)
!482 = !DILocation(line: 380, column: 13, scope: !250)
!483 = !DILocation(line: 0, scope: !250)
!484 = !DILocation(line: 380, column: 35, scope: !255)
!485 = !DILocation(line: 0, scope: !254)
!486 = !DILocation(line: 381, column: 17, scope: !254)
!487 = !DILocation(line: 381, column: 22, scope: !254)
!488 = !DILocation(line: 382, column: 32, scope: !254)
!489 = !DILocation(line: 383, column: 26, scope: !490)
!490 = distinct !DILexicalBlock(scope: !254, file: !3, line: 383, column: 21)
!491 = !DILocation(line: 383, column: 21, scope: !254)
!492 = !DILocation(line: 387, column: 13, scope: !255)
!493 = !DILocation(line: 380, column: 68, scope: !255)
!494 = !DILocation(line: 380, column: 13, scope: !255)
!495 = distinct !{!495, !482, !496}
!496 = !DILocation(line: 387, column: 13, scope: !250)
!497 = !DILocation(line: 389, column: 5, scope: !153)
!498 = !DILocation(line: 390, column: 1, scope: !153)
!499 = distinct !DISubprogram(name: "__wrap_vprintf", scope: !3, file: !3, line: 397, type: !500, scopeLine: 397, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !502)
!500 = !DISubroutineType(types: !501)
!501 = !{!12, !17, !159}
!502 = !{!503, !504}
!503 = !DILocalVariable(name: "format", arg: 1, scope: !499, file: !3, line: 397, type: !17)
!504 = !DILocalVariable(name: "args", arg: 2, scope: !499, file: !3, line: 397, type: !159)
!505 = !DILocation(line: 0, scope: !499)
!506 = !DILocation(line: 398, column: 12, scope: !499)
!507 = !DILocation(line: 398, column: 5, scope: !499)
!508 = distinct !DISubprogram(name: "__box_vprintf_write", scope: !3, file: !3, line: 392, type: !157, scopeLine: 392, flags: DIFlagPrototyped, spFlags: DISPFlagLocalToUnit | DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !509)
!509 = !{!510, !511, !512}
!510 = !DILocalVariable(name: "ctx", arg: 1, scope: !508, file: !3, line: 392, type: !6)
!511 = !DILocalVariable(name: "buf", arg: 2, scope: !508, file: !3, line: 392, type: !53)
!512 = !DILocalVariable(name: "size", arg: 3, scope: !508, file: !3, line: 392, type: !55)
!513 = !DILocation(line: 0, scope: !508)
!514 = !DILocation(line: 393, column: 24, scope: !508)
!515 = !DILocation(line: 393, column: 12, scope: !508)
!516 = !DILocalVariable(name: "a0", arg: 1, scope: !517, file: !3, line: 670, type: !22)
!517 = distinct !DISubprogram(name: "env___box_write", scope: !3, file: !3, line: 670, type: !518, scopeLine: 670, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !520)
!518 = !DISubroutineType(types: !519)
!519 = !{!22, !22, !7, !7}
!520 = !{!516, !521, !522}
!521 = !DILocalVariable(name: "a1", arg: 2, scope: !517, file: !3, line: 670, type: !7)
!522 = !DILocalVariable(name: "size", arg: 3, scope: !517, file: !3, line: 670, type: !7)
!523 = !DILocation(line: 0, scope: !517, inlinedAt: !524)
!524 = distinct !DILocation(line: 393, column: 12, scope: !508)
!525 = !DILocation(line: 672, column: 13, scope: !517, inlinedAt: !524)
!526 = !DILocalVariable(name: "off", arg: 1, scope: !527, file: !3, line: 446, type: !7)
!527 = distinct !DISubprogram(name: "to_ptr", scope: !3, file: !3, line: 446, type: !528, scopeLine: 446, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !530)
!528 = !DISubroutineType(types: !529)
!529 = !{!6, !7}
!530 = !{!526}
!531 = !DILocation(line: 0, scope: !527, inlinedAt: !532)
!532 = distinct !DILocation(line: 672, column: 43, scope: !517, inlinedAt: !524)
!533 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !532)
!534 = !DILocation(line: 671, column: 12, scope: !517, inlinedAt: !524)
!535 = !DILocation(line: 393, column: 5, scope: !508)
!536 = distinct !DISubprogram(name: "__wrap_printf", scope: !3, file: !3, line: 402, type: !537, scopeLine: 402, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !539)
!537 = !DISubroutineType(types: !538)
!538 = !{!12, !17, null}
!539 = !{!540, !541, !542}
!540 = !DILocalVariable(name: "format", arg: 1, scope: !536, file: !3, line: 402, type: !17)
!541 = !DILocalVariable(name: "args", scope: !536, file: !3, line: 403, type: !159)
!542 = !DILocalVariable(name: "res", scope: !536, file: !3, line: 405, type: !12)
!543 = !DILocation(line: 0, scope: !536)
!544 = !DILocation(line: 403, column: 5, scope: !536)
!545 = !DILocation(line: 404, column: 5, scope: !536)
!546 = !DILocation(line: 405, column: 19, scope: !536)
!547 = !DILocation(line: 406, column: 5, scope: !536)
!548 = !DILocation(line: 408, column: 1, scope: !536)
!549 = !DILocation(line: 407, column: 5, scope: !536)
!550 = distinct !DISubprogram(name: "__wrap_vfprintf", scope: !3, file: !3, line: 411, type: !551, scopeLine: 411, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !761)
!551 = !DISubroutineType(types: !552)
!552 = !{!12, !553, !17, !159}
!553 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !554, size: 32)
!554 = !DIDerivedType(tag: DW_TAG_typedef, name: "FILE", file: !555, line: 66, baseType: !556)
!555 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/stdio.h", directory: "")
!556 = !DIDerivedType(tag: DW_TAG_typedef, name: "__FILE", file: !557, line: 287, baseType: !558)
!557 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/sys/reent.h", directory: "")
!558 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "__sFILE", file: !557, line: 181, size: 832, elements: !559)
!559 = !{!560, !562, !563, !564, !565, !566, !571, !572, !573, !727, !731, !737, !741, !742, !743, !744, !746, !748, !749, !750, !752, !753, !759, !760}
!560 = !DIDerivedType(tag: DW_TAG_member, name: "_p", scope: !558, file: !557, line: 182, baseType: !561, size: 32)
!561 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !28, size: 32)
!562 = !DIDerivedType(tag: DW_TAG_member, name: "_r", scope: !558, file: !557, line: 183, baseType: !16, size: 32, offset: 32)
!563 = !DIDerivedType(tag: DW_TAG_member, name: "_w", scope: !558, file: !557, line: 184, baseType: !16, size: 32, offset: 64)
!564 = !DIDerivedType(tag: DW_TAG_member, name: "_flags", scope: !558, file: !557, line: 185, baseType: !37, size: 16, offset: 96)
!565 = !DIDerivedType(tag: DW_TAG_member, name: "_file", scope: !558, file: !557, line: 186, baseType: !37, size: 16, offset: 112)
!566 = !DIDerivedType(tag: DW_TAG_member, name: "_bf", scope: !558, file: !557, line: 187, baseType: !567, size: 64, offset: 128)
!567 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "__sbuf", file: !557, line: 117, size: 64, elements: !568)
!568 = !{!569, !570}
!569 = !DIDerivedType(tag: DW_TAG_member, name: "_base", scope: !567, file: !557, line: 118, baseType: !561, size: 32)
!570 = !DIDerivedType(tag: DW_TAG_member, name: "_size", scope: !567, file: !557, line: 119, baseType: !16, size: 32, offset: 32)
!571 = !DIDerivedType(tag: DW_TAG_member, name: "_lbfsize", scope: !558, file: !557, line: 188, baseType: !16, size: 32, offset: 192)
!572 = !DIDerivedType(tag: DW_TAG_member, name: "_cookie", scope: !558, file: !557, line: 195, baseType: !6, size: 32, offset: 224)
!573 = !DIDerivedType(tag: DW_TAG_member, name: "_read", scope: !558, file: !557, line: 197, baseType: !574, size: 32, offset: 256)
!574 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !575, size: 32)
!575 = !DISubroutineType(types: !576)
!576 = !{!16, !577, !6, !620, !16}
!577 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !578, size: 32)
!578 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_reent", file: !557, line: 608, size: 8512, elements: !579)
!579 = !{!580, !581, !583, !584, !585, !586, !590, !591, !594, !595, !599, !614, !615, !616, !618, !619, !621, !696, !715, !716, !718, !725}
!580 = !DIDerivedType(tag: DW_TAG_member, name: "_errno", scope: !578, file: !557, line: 610, baseType: !16, size: 32)
!581 = !DIDerivedType(tag: DW_TAG_member, name: "_stdin", scope: !578, file: !557, line: 615, baseType: !582, size: 32, offset: 32)
!582 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !556, size: 32)
!583 = !DIDerivedType(tag: DW_TAG_member, name: "_stdout", scope: !578, file: !557, line: 615, baseType: !582, size: 32, offset: 64)
!584 = !DIDerivedType(tag: DW_TAG_member, name: "_stderr", scope: !578, file: !557, line: 615, baseType: !582, size: 32, offset: 96)
!585 = !DIDerivedType(tag: DW_TAG_member, name: "_inc", scope: !578, file: !557, line: 617, baseType: !16, size: 32, offset: 128)
!586 = !DIDerivedType(tag: DW_TAG_member, name: "_emergency", scope: !578, file: !557, line: 618, baseType: !587, size: 200, offset: 160)
!587 = !DICompositeType(tag: DW_TAG_array_type, baseType: !19, size: 200, elements: !588)
!588 = !{!589}
!589 = !DISubrange(count: 25)
!590 = !DIDerivedType(tag: DW_TAG_member, name: "_unspecified_locale_info", scope: !578, file: !557, line: 621, baseType: !16, size: 32, offset: 384)
!591 = !DIDerivedType(tag: DW_TAG_member, name: "_locale", scope: !578, file: !557, line: 622, baseType: !592, size: 32, offset: 416)
!592 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !593, size: 32)
!593 = !DICompositeType(tag: DW_TAG_structure_type, name: "__locale_t", file: !557, line: 40, flags: DIFlagFwdDecl)
!594 = !DIDerivedType(tag: DW_TAG_member, name: "__sdidinit", scope: !578, file: !557, line: 624, baseType: !16, size: 32, offset: 448)
!595 = !DIDerivedType(tag: DW_TAG_member, name: "__cleanup", scope: !578, file: !557, line: 626, baseType: !596, size: 32, offset: 480)
!596 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !597, size: 32)
!597 = !DISubroutineType(types: !598)
!598 = !{null, !577}
!599 = !DIDerivedType(tag: DW_TAG_member, name: "_result", scope: !578, file: !557, line: 629, baseType: !600, size: 32, offset: 512)
!600 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !601, size: 32)
!601 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_Bigint", file: !557, line: 47, size: 192, elements: !602)
!602 = !{!603, !604, !605, !606, !607, !608}
!603 = !DIDerivedType(tag: DW_TAG_member, name: "_next", scope: !601, file: !557, line: 49, baseType: !600, size: 32)
!604 = !DIDerivedType(tag: DW_TAG_member, name: "_k", scope: !601, file: !557, line: 50, baseType: !16, size: 32, offset: 32)
!605 = !DIDerivedType(tag: DW_TAG_member, name: "_maxwds", scope: !601, file: !557, line: 50, baseType: !16, size: 32, offset: 64)
!606 = !DIDerivedType(tag: DW_TAG_member, name: "_sign", scope: !601, file: !557, line: 50, baseType: !16, size: 32, offset: 96)
!607 = !DIDerivedType(tag: DW_TAG_member, name: "_wds", scope: !601, file: !557, line: 50, baseType: !16, size: 32, offset: 128)
!608 = !DIDerivedType(tag: DW_TAG_member, name: "_x", scope: !601, file: !557, line: 51, baseType: !609, size: 32, offset: 160)
!609 = !DICompositeType(tag: DW_TAG_array_type, baseType: !610, size: 32, elements: !612)
!610 = !DIDerivedType(tag: DW_TAG_typedef, name: "__ULong", file: !557, line: 22, baseType: !611)
!611 = !DIBasicType(name: "long unsigned int", size: 32, encoding: DW_ATE_unsigned)
!612 = !{!613}
!613 = !DISubrange(count: 1)
!614 = !DIDerivedType(tag: DW_TAG_member, name: "_result_k", scope: !578, file: !557, line: 630, baseType: !16, size: 32, offset: 544)
!615 = !DIDerivedType(tag: DW_TAG_member, name: "_p5s", scope: !578, file: !557, line: 631, baseType: !600, size: 32, offset: 576)
!616 = !DIDerivedType(tag: DW_TAG_member, name: "_freelist", scope: !578, file: !557, line: 632, baseType: !617, size: 32, offset: 608)
!617 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !600, size: 32)
!618 = !DIDerivedType(tag: DW_TAG_member, name: "_cvtlen", scope: !578, file: !557, line: 635, baseType: !16, size: 32, offset: 640)
!619 = !DIDerivedType(tag: DW_TAG_member, name: "_cvtbuf", scope: !578, file: !557, line: 636, baseType: !620, size: 32, offset: 672)
!620 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !19, size: 32)
!621 = !DIDerivedType(tag: DW_TAG_member, name: "_new", scope: !578, file: !557, line: 671, baseType: !622, size: 1920, offset: 704)
!622 = distinct !DICompositeType(tag: DW_TAG_union_type, scope: !578, file: !557, line: 638, size: 1920, elements: !623)
!623 = !{!624, !687}
!624 = !DIDerivedType(tag: DW_TAG_member, name: "_reent", scope: !622, file: !557, line: 661, baseType: !625, size: 1664)
!625 = distinct !DICompositeType(tag: DW_TAG_structure_type, scope: !622, file: !557, line: 640, size: 1664, elements: !626)
!626 = !{!627, !628, !629, !633, !645, !646, !648, !658, !670, !671, !672, !676, !680, !681, !682, !683, !684, !685, !686}
!627 = !DIDerivedType(tag: DW_TAG_member, name: "_unused_rand", scope: !625, file: !557, line: 642, baseType: !11, size: 32)
!628 = !DIDerivedType(tag: DW_TAG_member, name: "_strtok_last", scope: !625, file: !557, line: 643, baseType: !620, size: 32, offset: 32)
!629 = !DIDerivedType(tag: DW_TAG_member, name: "_asctime_buf", scope: !625, file: !557, line: 644, baseType: !630, size: 208, offset: 64)
!630 = !DICompositeType(tag: DW_TAG_array_type, baseType: !19, size: 208, elements: !631)
!631 = !{!632}
!632 = !DISubrange(count: 26)
!633 = !DIDerivedType(tag: DW_TAG_member, name: "_localtime_buf", scope: !625, file: !557, line: 645, baseType: !634, size: 288, offset: 288)
!634 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "__tm", file: !557, line: 55, size: 288, elements: !635)
!635 = !{!636, !637, !638, !639, !640, !641, !642, !643, !644}
!636 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_sec", scope: !634, file: !557, line: 57, baseType: !16, size: 32)
!637 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_min", scope: !634, file: !557, line: 58, baseType: !16, size: 32, offset: 32)
!638 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_hour", scope: !634, file: !557, line: 59, baseType: !16, size: 32, offset: 64)
!639 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_mday", scope: !634, file: !557, line: 60, baseType: !16, size: 32, offset: 96)
!640 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_mon", scope: !634, file: !557, line: 61, baseType: !16, size: 32, offset: 128)
!641 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_year", scope: !634, file: !557, line: 62, baseType: !16, size: 32, offset: 160)
!642 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_wday", scope: !634, file: !557, line: 63, baseType: !16, size: 32, offset: 192)
!643 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_yday", scope: !634, file: !557, line: 64, baseType: !16, size: 32, offset: 224)
!644 = !DIDerivedType(tag: DW_TAG_member, name: "__tm_isdst", scope: !634, file: !557, line: 65, baseType: !16, size: 32, offset: 256)
!645 = !DIDerivedType(tag: DW_TAG_member, name: "_gamma_signgam", scope: !625, file: !557, line: 646, baseType: !16, size: 32, offset: 576)
!646 = !DIDerivedType(tag: DW_TAG_member, name: "_rand_next", scope: !625, file: !557, line: 647, baseType: !647, size: 64, offset: 640)
!647 = !DIBasicType(name: "long long unsigned int", size: 64, encoding: DW_ATE_unsigned)
!648 = !DIDerivedType(tag: DW_TAG_member, name: "_r48", scope: !625, file: !557, line: 648, baseType: !649, size: 112, offset: 704)
!649 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_rand48", file: !557, line: 319, size: 112, elements: !650)
!650 = !{!651, !656, !657}
!651 = !DIDerivedType(tag: DW_TAG_member, name: "_seed", scope: !649, file: !557, line: 320, baseType: !652, size: 48)
!652 = !DICompositeType(tag: DW_TAG_array_type, baseType: !653, size: 48, elements: !654)
!653 = !DIBasicType(name: "unsigned short", size: 16, encoding: DW_ATE_unsigned)
!654 = !{!655}
!655 = !DISubrange(count: 3)
!656 = !DIDerivedType(tag: DW_TAG_member, name: "_mult", scope: !649, file: !557, line: 321, baseType: !652, size: 48, offset: 48)
!657 = !DIDerivedType(tag: DW_TAG_member, name: "_add", scope: !649, file: !557, line: 322, baseType: !653, size: 16, offset: 96)
!658 = !DIDerivedType(tag: DW_TAG_member, name: "_mblen_state", scope: !625, file: !557, line: 649, baseType: !659, size: 64, offset: 832)
!659 = !DIDerivedType(tag: DW_TAG_typedef, name: "_mbstate_t", file: !15, line: 171, baseType: !660)
!660 = distinct !DICompositeType(tag: DW_TAG_structure_type, file: !15, line: 163, size: 64, elements: !661)
!661 = !{!662, !663}
!662 = !DIDerivedType(tag: DW_TAG_member, name: "__count", scope: !660, file: !15, line: 165, baseType: !16, size: 32)
!663 = !DIDerivedType(tag: DW_TAG_member, name: "__value", scope: !660, file: !15, line: 170, baseType: !664, size: 32, offset: 32)
!664 = distinct !DICompositeType(tag: DW_TAG_union_type, scope: !660, file: !15, line: 166, size: 32, elements: !665)
!665 = !{!666, !668}
!666 = !DIDerivedType(tag: DW_TAG_member, name: "__wch", scope: !664, file: !15, line: 168, baseType: !667, size: 32)
!667 = !DIDerivedType(tag: DW_TAG_typedef, name: "wint_t", file: !56, line: 116, baseType: !16)
!668 = !DIDerivedType(tag: DW_TAG_member, name: "__wchb", scope: !664, file: !15, line: 169, baseType: !669, size: 32)
!669 = !DICompositeType(tag: DW_TAG_array_type, baseType: !28, size: 32, elements: !69)
!670 = !DIDerivedType(tag: DW_TAG_member, name: "_mbtowc_state", scope: !625, file: !557, line: 650, baseType: !659, size: 64, offset: 896)
!671 = !DIDerivedType(tag: DW_TAG_member, name: "_wctomb_state", scope: !625, file: !557, line: 651, baseType: !659, size: 64, offset: 960)
!672 = !DIDerivedType(tag: DW_TAG_member, name: "_l64a_buf", scope: !625, file: !557, line: 652, baseType: !673, size: 64, offset: 1024)
!673 = !DICompositeType(tag: DW_TAG_array_type, baseType: !19, size: 64, elements: !674)
!674 = !{!675}
!675 = !DISubrange(count: 8)
!676 = !DIDerivedType(tag: DW_TAG_member, name: "_signal_buf", scope: !625, file: !557, line: 653, baseType: !677, size: 192, offset: 1088)
!677 = !DICompositeType(tag: DW_TAG_array_type, baseType: !19, size: 192, elements: !678)
!678 = !{!679}
!679 = !DISubrange(count: 24)
!680 = !DIDerivedType(tag: DW_TAG_member, name: "_getdate_err", scope: !625, file: !557, line: 654, baseType: !16, size: 32, offset: 1280)
!681 = !DIDerivedType(tag: DW_TAG_member, name: "_mbrlen_state", scope: !625, file: !557, line: 655, baseType: !659, size: 64, offset: 1312)
!682 = !DIDerivedType(tag: DW_TAG_member, name: "_mbrtowc_state", scope: !625, file: !557, line: 656, baseType: !659, size: 64, offset: 1376)
!683 = !DIDerivedType(tag: DW_TAG_member, name: "_mbsrtowcs_state", scope: !625, file: !557, line: 657, baseType: !659, size: 64, offset: 1440)
!684 = !DIDerivedType(tag: DW_TAG_member, name: "_wcrtomb_state", scope: !625, file: !557, line: 658, baseType: !659, size: 64, offset: 1504)
!685 = !DIDerivedType(tag: DW_TAG_member, name: "_wcsrtombs_state", scope: !625, file: !557, line: 659, baseType: !659, size: 64, offset: 1568)
!686 = !DIDerivedType(tag: DW_TAG_member, name: "_h_errno", scope: !625, file: !557, line: 660, baseType: !16, size: 32, offset: 1632)
!687 = !DIDerivedType(tag: DW_TAG_member, name: "_unused", scope: !622, file: !557, line: 670, baseType: !688, size: 1920)
!688 = distinct !DICompositeType(tag: DW_TAG_structure_type, scope: !622, file: !557, line: 665, size: 1920, elements: !689)
!689 = !{!690, !694}
!690 = !DIDerivedType(tag: DW_TAG_member, name: "_nextf", scope: !688, file: !557, line: 668, baseType: !691, size: 960)
!691 = !DICompositeType(tag: DW_TAG_array_type, baseType: !561, size: 960, elements: !692)
!692 = !{!693}
!693 = !DISubrange(count: 30)
!694 = !DIDerivedType(tag: DW_TAG_member, name: "_nmalloc", scope: !688, file: !557, line: 669, baseType: !695, size: 960, offset: 960)
!695 = !DICompositeType(tag: DW_TAG_array_type, baseType: !11, size: 960, elements: !692)
!696 = !DIDerivedType(tag: DW_TAG_member, name: "_atexit", scope: !578, file: !557, line: 675, baseType: !697, size: 32, offset: 2624)
!697 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !698, size: 32)
!698 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_atexit", file: !557, line: 93, size: 3200, elements: !699)
!699 = !{!700, !701, !702, !707}
!700 = !DIDerivedType(tag: DW_TAG_member, name: "_next", scope: !698, file: !557, line: 94, baseType: !697, size: 32)
!701 = !DIDerivedType(tag: DW_TAG_member, name: "_ind", scope: !698, file: !557, line: 95, baseType: !16, size: 32, offset: 32)
!702 = !DIDerivedType(tag: DW_TAG_member, name: "_fns", scope: !698, file: !557, line: 97, baseType: !703, size: 1024, offset: 64)
!703 = !DICompositeType(tag: DW_TAG_array_type, baseType: !704, size: 1024, elements: !705)
!704 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !102, size: 32)
!705 = !{!706}
!706 = !DISubrange(count: 32)
!707 = !DIDerivedType(tag: DW_TAG_member, name: "_on_exit_args", scope: !698, file: !557, line: 98, baseType: !708, size: 2112, offset: 1088)
!708 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_on_exit_args", file: !557, line: 74, size: 2112, elements: !709)
!709 = !{!710, !712, !713, !714}
!710 = !DIDerivedType(tag: DW_TAG_member, name: "_fnargs", scope: !708, file: !557, line: 75, baseType: !711, size: 1024)
!711 = !DICompositeType(tag: DW_TAG_array_type, baseType: !6, size: 1024, elements: !705)
!712 = !DIDerivedType(tag: DW_TAG_member, name: "_dso_handle", scope: !708, file: !557, line: 76, baseType: !711, size: 1024, offset: 1024)
!713 = !DIDerivedType(tag: DW_TAG_member, name: "_fntypes", scope: !708, file: !557, line: 78, baseType: !610, size: 32, offset: 2048)
!714 = !DIDerivedType(tag: DW_TAG_member, name: "_is_cxa", scope: !708, file: !557, line: 81, baseType: !610, size: 32, offset: 2080)
!715 = !DIDerivedType(tag: DW_TAG_member, name: "_atexit0", scope: !578, file: !557, line: 676, baseType: !698, size: 3200, offset: 2656)
!716 = !DIDerivedType(tag: DW_TAG_member, name: "_sig_func", scope: !578, file: !557, line: 680, baseType: !717, size: 32, offset: 5856)
!717 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !47, size: 32)
!718 = !DIDerivedType(tag: DW_TAG_member, name: "__sglue", scope: !578, file: !557, line: 685, baseType: !719, size: 96, offset: 5888)
!719 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "_glue", file: !557, line: 291, size: 96, elements: !720)
!720 = !{!721, !723, !724}
!721 = !DIDerivedType(tag: DW_TAG_member, name: "_next", scope: !719, file: !557, line: 293, baseType: !722, size: 32)
!722 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !719, size: 32)
!723 = !DIDerivedType(tag: DW_TAG_member, name: "_niobs", scope: !719, file: !557, line: 294, baseType: !16, size: 32, offset: 32)
!724 = !DIDerivedType(tag: DW_TAG_member, name: "_iobs", scope: !719, file: !557, line: 295, baseType: !582, size: 32, offset: 64)
!725 = !DIDerivedType(tag: DW_TAG_member, name: "__sf", scope: !578, file: !557, line: 687, baseType: !726, size: 2496, offset: 5984)
!726 = !DICompositeType(tag: DW_TAG_array_type, baseType: !556, size: 2496, elements: !654)
!727 = !DIDerivedType(tag: DW_TAG_member, name: "_write", scope: !558, file: !557, line: 199, baseType: !728, size: 32, offset: 288)
!728 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !729, size: 32)
!729 = !DISubroutineType(types: !730)
!730 = !{!16, !577, !6, !17, !16}
!731 = !DIDerivedType(tag: DW_TAG_member, name: "_seek", scope: !558, file: !557, line: 202, baseType: !732, size: 32, offset: 320)
!732 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !733, size: 32)
!733 = !DISubroutineType(types: !734)
!734 = !{!735, !577, !6, !735, !16}
!735 = !DIDerivedType(tag: DW_TAG_typedef, name: "_fpos_t", file: !15, line: 114, baseType: !736)
!736 = !DIBasicType(name: "long int", size: 32, encoding: DW_ATE_signed)
!737 = !DIDerivedType(tag: DW_TAG_member, name: "_close", scope: !558, file: !557, line: 203, baseType: !738, size: 32, offset: 352)
!738 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !739, size: 32)
!739 = !DISubroutineType(types: !740)
!740 = !{!16, !577, !6}
!741 = !DIDerivedType(tag: DW_TAG_member, name: "_ub", scope: !558, file: !557, line: 206, baseType: !567, size: 64, offset: 384)
!742 = !DIDerivedType(tag: DW_TAG_member, name: "_up", scope: !558, file: !557, line: 207, baseType: !561, size: 32, offset: 448)
!743 = !DIDerivedType(tag: DW_TAG_member, name: "_ur", scope: !558, file: !557, line: 208, baseType: !16, size: 32, offset: 480)
!744 = !DIDerivedType(tag: DW_TAG_member, name: "_ubuf", scope: !558, file: !557, line: 211, baseType: !745, size: 24, offset: 512)
!745 = !DICompositeType(tag: DW_TAG_array_type, baseType: !28, size: 24, elements: !654)
!746 = !DIDerivedType(tag: DW_TAG_member, name: "_nbuf", scope: !558, file: !557, line: 212, baseType: !747, size: 8, offset: 536)
!747 = !DICompositeType(tag: DW_TAG_array_type, baseType: !28, size: 8, elements: !612)
!748 = !DIDerivedType(tag: DW_TAG_member, name: "_lb", scope: !558, file: !557, line: 215, baseType: !567, size: 64, offset: 544)
!749 = !DIDerivedType(tag: DW_TAG_member, name: "_blksize", scope: !558, file: !557, line: 218, baseType: !16, size: 32, offset: 608)
!750 = !DIDerivedType(tag: DW_TAG_member, name: "_offset", scope: !558, file: !557, line: 219, baseType: !751, size: 32, offset: 640)
!751 = !DIDerivedType(tag: DW_TAG_typedef, name: "_off_t", file: !15, line: 44, baseType: !736)
!752 = !DIDerivedType(tag: DW_TAG_member, name: "_data", scope: !558, file: !557, line: 222, baseType: !577, size: 32, offset: 672)
!753 = !DIDerivedType(tag: DW_TAG_member, name: "_lock", scope: !558, file: !557, line: 226, baseType: !754, size: 32, offset: 704)
!754 = !DIDerivedType(tag: DW_TAG_typedef, name: "_flock_t", file: !15, line: 175, baseType: !755)
!755 = !DIDerivedType(tag: DW_TAG_typedef, name: "_LOCK_T", file: !756, line: 34, baseType: !757)
!756 = !DIFile(filename: "/usr/bin/../arm-none-eabi/include/sys/lock.h", directory: "")
!757 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !758, size: 32)
!758 = !DICompositeType(tag: DW_TAG_structure_type, name: "__lock", file: !756, line: 33, flags: DIFlagFwdDecl)
!759 = !DIDerivedType(tag: DW_TAG_member, name: "_mbstate", scope: !558, file: !557, line: 228, baseType: !659, size: 64, offset: 736)
!760 = !DIDerivedType(tag: DW_TAG_member, name: "_flags2", scope: !558, file: !557, line: 229, baseType: !16, size: 32, offset: 800)
!761 = !{!762, !763, !764, !765}
!762 = !DILocalVariable(name: "f", arg: 1, scope: !550, file: !3, line: 411, type: !553)
!763 = !DILocalVariable(name: "format", arg: 2, scope: !550, file: !3, line: 411, type: !17)
!764 = !DILocalVariable(name: "args", arg: 3, scope: !550, file: !3, line: 411, type: !159)
!765 = !DILocalVariable(name: "fd", scope: !550, file: !3, line: 412, type: !22)
!766 = !DILocation(line: 0, scope: !550)
!767 = !DILocation(line: 412, column: 24, scope: !550)
!768 = !{!769, !92, i64 8}
!769 = !{!"_reent", !113, i64 0, !92, i64 4, !92, i64 8, !92, i64 12, !113, i64 16, !93, i64 20, !113, i64 48, !92, i64 52, !113, i64 56, !92, i64 60, !92, i64 64, !113, i64 68, !92, i64 72, !92, i64 76, !113, i64 80, !92, i64 84, !93, i64 88, !92, i64 328, !770, i64 332, !92, i64 732, !773, i64 736, !93, i64 748}
!770 = !{!"_atexit", !92, i64 0, !113, i64 4, !93, i64 8, !771, i64 136}
!771 = !{!"_on_exit_args", !93, i64 0, !93, i64 128, !772, i64 256, !772, i64 260}
!772 = !{!"long", !93, i64 0}
!773 = !{!"_glue", !92, i64 0, !113, i64 4, !92, i64 8}
!774 = !DILocation(line: 412, column: 21, scope: !550)
!775 = !DILocation(line: 413, column: 48, scope: !550)
!776 = !DILocation(line: 413, column: 12, scope: !550)
!777 = !DILocation(line: 413, column: 5, scope: !550)
!778 = distinct !DISubprogram(name: "__wrap_fprintf", scope: !3, file: !3, line: 417, type: !779, scopeLine: 417, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !781)
!779 = !DISubroutineType(types: !780)
!780 = !{!12, !553, !17, null}
!781 = !{!782, !783, !784, !785}
!782 = !DILocalVariable(name: "f", arg: 1, scope: !778, file: !3, line: 417, type: !553)
!783 = !DILocalVariable(name: "format", arg: 2, scope: !778, file: !3, line: 417, type: !17)
!784 = !DILocalVariable(name: "args", scope: !778, file: !3, line: 418, type: !159)
!785 = !DILocalVariable(name: "res", scope: !778, file: !3, line: 420, type: !12)
!786 = !DILocation(line: 0, scope: !778)
!787 = !DILocation(line: 418, column: 5, scope: !778)
!788 = !DILocation(line: 419, column: 5, scope: !778)
!789 = !DILocation(line: 420, column: 19, scope: !778)
!790 = !DILocation(line: 421, column: 5, scope: !778)
!791 = !DILocation(line: 423, column: 1, scope: !778)
!792 = !DILocation(line: 422, column: 5, scope: !778)
!793 = distinct !DISubprogram(name: "__wrap_fflush", scope: !3, file: !3, line: 426, type: !794, scopeLine: 426, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !796)
!794 = !DISubroutineType(types: !795)
!795 = !{!16, !553}
!796 = !{!797, !798}
!797 = !DILocalVariable(name: "f", arg: 1, scope: !793, file: !3, line: 426, type: !553)
!798 = !DILocalVariable(name: "fd", scope: !793, file: !3, line: 427, type: !22)
!799 = !DILocation(line: 0, scope: !793)
!800 = !DILocation(line: 427, column: 24, scope: !793)
!801 = !DILocation(line: 427, column: 21, scope: !793)
!802 = !DILocation(line: 427, column: 18, scope: !793)
!803 = !DILocalVariable(name: "a0", arg: 1, scope: !804, file: !3, line: 675, type: !22)
!804 = distinct !DISubprogram(name: "env___box_flush", scope: !3, file: !3, line: 675, type: !805, scopeLine: 675, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !807)
!805 = !DISubroutineType(types: !806)
!806 = !{!22, !22}
!807 = !{!803}
!808 = !DILocation(line: 0, scope: !804, inlinedAt: !809)
!809 = distinct !DILocation(line: 428, column: 12, scope: !793)
!810 = !DILocation(line: 677, column: 13, scope: !804, inlinedAt: !809)
!811 = !DILocation(line: 676, column: 12, scope: !804, inlinedAt: !809)
!812 = !DILocation(line: 428, column: 5, scope: !793)
!813 = distinct !DISubprogram(name: "_write", scope: !3, file: !3, line: 432, type: !814, scopeLine: 432, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !816)
!814 = !DISubroutineType(types: !815)
!815 = !{!16, !16, !17, !16}
!816 = !{!817, !818, !819}
!817 = !DILocalVariable(name: "handle", arg: 1, scope: !813, file: !3, line: 432, type: !16)
!818 = !DILocalVariable(name: "buffer", arg: 2, scope: !813, file: !3, line: 432, type: !17)
!819 = !DILocalVariable(name: "size", arg: 3, scope: !813, file: !3, line: 432, type: !16)
!820 = !DILocation(line: 0, scope: !813)
!821 = !DILocation(line: 433, column: 12, scope: !813)
!822 = !DILocation(line: 0, scope: !517, inlinedAt: !823)
!823 = distinct !DILocation(line: 433, column: 12, scope: !813)
!824 = !DILocation(line: 672, column: 13, scope: !517, inlinedAt: !823)
!825 = !DILocation(line: 0, scope: !527, inlinedAt: !826)
!826 = distinct !DILocation(line: 672, column: 43, scope: !517, inlinedAt: !823)
!827 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !826)
!828 = !DILocation(line: 671, column: 12, scope: !517, inlinedAt: !823)
!829 = !DILocation(line: 433, column: 5, scope: !813)
!830 = !DILocation(line: 0, scope: !527)
!831 = !DILocation(line: 447, column: 13, scope: !527)
!832 = !DILocation(line: 447, column: 5, scope: !527)
!833 = distinct !DISubprogram(name: "from_ptr", scope: !3, file: !3, line: 451, type: !834, scopeLine: 451, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !836)
!834 = !DISubroutineType(types: !835)
!835 = !{!7, !53}
!836 = !{!837}
!837 = !DILocalVariable(name: "ptr", arg: 1, scope: !833, file: !3, line: 451, type: !53)
!838 = !DILocation(line: 0, scope: !833)
!839 = !DILocation(line: 452, column: 26, scope: !833)
!840 = !DILocation(line: 452, column: 5, scope: !833)
!841 = distinct !DISubprogram(name: "get_i8", scope: !3, file: !3, line: 456, type: !842, scopeLine: 456, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !844)
!842 = !DISubroutineType(types: !843)
!843 = !{!31, !7}
!844 = !{!845}
!845 = !DILocalVariable(name: "off", arg: 1, scope: !841, file: !3, line: 456, type: !7)
!846 = !DILocation(line: 0, scope: !841)
!847 = !DILocation(line: 457, column: 15, scope: !841)
!848 = !DILocation(line: 0, scope: !527, inlinedAt: !849)
!849 = distinct !DILocation(line: 458, column: 22, scope: !841)
!850 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !849)
!851 = !DILocation(line: 458, column: 12, scope: !841)
!852 = !DILocation(line: 458, column: 5, scope: !841)
!853 = distinct !DISubprogram(name: "get_i16", scope: !3, file: !3, line: 462, type: !854, scopeLine: 462, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !856)
!854 = !DISubroutineType(types: !855)
!855 = !{!35, !7}
!856 = !{!857}
!857 = !DILocalVariable(name: "off", arg: 1, scope: !853, file: !3, line: 462, type: !7)
!858 = !DILocation(line: 0, scope: !853)
!859 = !DILocation(line: 463, column: 15, scope: !853)
!860 = !DILocation(line: 0, scope: !527, inlinedAt: !861)
!861 = distinct !DILocation(line: 464, column: 23, scope: !853)
!862 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !861)
!863 = !DILocation(line: 464, column: 13, scope: !853)
!864 = !DILocation(line: 464, column: 12, scope: !853)
!865 = !{!866, !866, i64 0}
!866 = !{!"short", !93, i64 0}
!867 = !DILocation(line: 464, column: 5, scope: !853)
!868 = distinct !DISubprogram(name: "get_i32", scope: !3, file: !3, line: 468, type: !869, scopeLine: 468, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !871)
!869 = !DISubroutineType(types: !870)
!870 = !{!22, !7}
!871 = !{!872}
!872 = !DILocalVariable(name: "off", arg: 1, scope: !868, file: !3, line: 468, type: !7)
!873 = !DILocation(line: 0, scope: !868)
!874 = !DILocation(line: 469, column: 15, scope: !868)
!875 = !DILocation(line: 0, scope: !527, inlinedAt: !876)
!876 = distinct !DILocation(line: 470, column: 23, scope: !868)
!877 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !876)
!878 = !DILocation(line: 470, column: 13, scope: !868)
!879 = !DILocation(line: 470, column: 12, scope: !868)
!880 = !DILocation(line: 470, column: 5, scope: !868)
!881 = distinct !DISubprogram(name: "get_i64", scope: !3, file: !3, line: 474, type: !882, scopeLine: 474, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !884)
!882 = !DISubroutineType(types: !883)
!883 = !{!40, !7}
!884 = !{!885}
!885 = !DILocalVariable(name: "off", arg: 1, scope: !881, file: !3, line: 474, type: !7)
!886 = !DILocation(line: 0, scope: !881)
!887 = !DILocation(line: 475, column: 15, scope: !881)
!888 = !DILocation(line: 0, scope: !527, inlinedAt: !889)
!889 = distinct !DILocation(line: 476, column: 23, scope: !881)
!890 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !889)
!891 = !DILocation(line: 476, column: 13, scope: !881)
!892 = !DILocation(line: 476, column: 12, scope: !881)
!893 = !{!894, !894, i64 0}
!894 = !{!"long long", !93, i64 0}
!895 = !DILocation(line: 476, column: 5, scope: !881)
!896 = distinct !DISubprogram(name: "get_f32", scope: !3, file: !3, line: 480, type: !897, scopeLine: 480, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !899)
!897 = !DISubroutineType(types: !898)
!898 = !{!44, !7}
!899 = !{!900}
!900 = !DILocalVariable(name: "off", arg: 1, scope: !896, file: !3, line: 480, type: !7)
!901 = !DILocation(line: 0, scope: !896)
!902 = !DILocation(line: 481, column: 15, scope: !896)
!903 = !DILocation(line: 0, scope: !527, inlinedAt: !904)
!904 = distinct !DILocation(line: 482, column: 21, scope: !896)
!905 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !904)
!906 = !DILocation(line: 482, column: 13, scope: !896)
!907 = !DILocation(line: 482, column: 12, scope: !896)
!908 = !{!909, !909, i64 0}
!909 = !{!"float", !93, i64 0}
!910 = !DILocation(line: 482, column: 5, scope: !896)
!911 = distinct !DISubprogram(name: "get_f64", scope: !3, file: !3, line: 486, type: !912, scopeLine: 486, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !914)
!912 = !DISubroutineType(types: !913)
!913 = !{!46, !7}
!914 = !{!915}
!915 = !DILocalVariable(name: "off", arg: 1, scope: !911, file: !3, line: 486, type: !7)
!916 = !DILocation(line: 0, scope: !911)
!917 = !DILocation(line: 487, column: 15, scope: !911)
!918 = !DILocation(line: 0, scope: !527, inlinedAt: !919)
!919 = distinct !DILocation(line: 488, column: 22, scope: !911)
!920 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !919)
!921 = !DILocation(line: 488, column: 13, scope: !911)
!922 = !DILocation(line: 488, column: 12, scope: !911)
!923 = !{!924, !924, i64 0}
!924 = !{!"double", !93, i64 0}
!925 = !DILocation(line: 488, column: 5, scope: !911)
!926 = distinct !DISubprogram(name: "set_i8", scope: !3, file: !3, line: 492, type: !927, scopeLine: 492, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !929)
!927 = !DISubroutineType(types: !928)
!928 = !{null, !7, !31}
!929 = !{!930, !931}
!930 = !DILocalVariable(name: "off", arg: 1, scope: !926, file: !3, line: 492, type: !7)
!931 = !DILocalVariable(name: "v", arg: 2, scope: !926, file: !3, line: 492, type: !31)
!932 = !DILocation(line: 0, scope: !926)
!933 = !DILocation(line: 493, column: 15, scope: !926)
!934 = !DILocation(line: 0, scope: !527, inlinedAt: !935)
!935 = distinct !DILocation(line: 494, column: 15, scope: !926)
!936 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !935)
!937 = !DILocation(line: 494, column: 27, scope: !926)
!938 = !DILocation(line: 495, column: 1, scope: !926)
!939 = distinct !DISubprogram(name: "set_i16", scope: !3, file: !3, line: 498, type: !940, scopeLine: 498, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !942)
!940 = !DISubroutineType(types: !941)
!941 = !{null, !7, !35}
!942 = !{!943, !944}
!943 = !DILocalVariable(name: "off", arg: 1, scope: !939, file: !3, line: 498, type: !7)
!944 = !DILocalVariable(name: "v", arg: 2, scope: !939, file: !3, line: 498, type: !35)
!945 = !DILocation(line: 0, scope: !939)
!946 = !DILocation(line: 499, column: 15, scope: !939)
!947 = !DILocation(line: 0, scope: !527, inlinedAt: !948)
!948 = distinct !DILocation(line: 500, column: 16, scope: !939)
!949 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !948)
!950 = !DILocation(line: 500, column: 6, scope: !939)
!951 = !DILocation(line: 500, column: 28, scope: !939)
!952 = !DILocation(line: 501, column: 1, scope: !939)
!953 = distinct !DISubprogram(name: "set_i32", scope: !3, file: !3, line: 504, type: !954, scopeLine: 504, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !956)
!954 = !DISubroutineType(types: !955)
!955 = !{null, !7, !22}
!956 = !{!957, !958}
!957 = !DILocalVariable(name: "off", arg: 1, scope: !953, file: !3, line: 504, type: !7)
!958 = !DILocalVariable(name: "v", arg: 2, scope: !953, file: !3, line: 504, type: !22)
!959 = !DILocation(line: 0, scope: !953)
!960 = !DILocation(line: 505, column: 15, scope: !953)
!961 = !DILocation(line: 0, scope: !527, inlinedAt: !962)
!962 = distinct !DILocation(line: 506, column: 16, scope: !953)
!963 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !962)
!964 = !DILocation(line: 506, column: 6, scope: !953)
!965 = !DILocation(line: 506, column: 28, scope: !953)
!966 = !DILocation(line: 507, column: 1, scope: !953)
!967 = distinct !DISubprogram(name: "set_i64", scope: !3, file: !3, line: 510, type: !968, scopeLine: 510, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !970)
!968 = !DISubroutineType(types: !969)
!969 = !{null, !7, !40}
!970 = !{!971, !972}
!971 = !DILocalVariable(name: "off", arg: 1, scope: !967, file: !3, line: 510, type: !7)
!972 = !DILocalVariable(name: "v", arg: 2, scope: !967, file: !3, line: 510, type: !40)
!973 = !DILocation(line: 0, scope: !967)
!974 = !DILocation(line: 511, column: 15, scope: !967)
!975 = !DILocation(line: 0, scope: !527, inlinedAt: !976)
!976 = distinct !DILocation(line: 512, column: 16, scope: !967)
!977 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !976)
!978 = !DILocation(line: 512, column: 6, scope: !967)
!979 = !DILocation(line: 512, column: 28, scope: !967)
!980 = !DILocation(line: 513, column: 1, scope: !967)
!981 = distinct !DISubprogram(name: "set_f32", scope: !3, file: !3, line: 516, type: !982, scopeLine: 516, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !984)
!982 = !DISubroutineType(types: !983)
!983 = !{null, !7, !44}
!984 = !{!985, !986}
!985 = !DILocalVariable(name: "off", arg: 1, scope: !981, file: !3, line: 516, type: !7)
!986 = !DILocalVariable(name: "v", arg: 2, scope: !981, file: !3, line: 516, type: !44)
!987 = !DILocation(line: 0, scope: !981)
!988 = !DILocation(line: 517, column: 15, scope: !981)
!989 = !DILocation(line: 0, scope: !527, inlinedAt: !990)
!990 = distinct !DILocation(line: 518, column: 14, scope: !981)
!991 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !990)
!992 = !DILocation(line: 518, column: 6, scope: !981)
!993 = !DILocation(line: 518, column: 26, scope: !981)
!994 = !DILocation(line: 519, column: 1, scope: !981)
!995 = distinct !DISubprogram(name: "set_f64", scope: !3, file: !3, line: 522, type: !996, scopeLine: 522, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !998)
!996 = !DISubroutineType(types: !997)
!997 = !{null, !7, !46}
!998 = !{!999, !1000}
!999 = !DILocalVariable(name: "off", arg: 1, scope: !995, file: !3, line: 522, type: !7)
!1000 = !DILocalVariable(name: "v", arg: 2, scope: !995, file: !3, line: 522, type: !46)
!1001 = !DILocation(line: 0, scope: !995)
!1002 = !DILocation(line: 523, column: 15, scope: !995)
!1003 = !DILocation(line: 0, scope: !527, inlinedAt: !1004)
!1004 = distinct !DILocation(line: 524, column: 15, scope: !995)
!1005 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !1004)
!1006 = !DILocation(line: 524, column: 6, scope: !995)
!1007 = !DILocation(line: 524, column: 27, scope: !995)
!1008 = !DILocation(line: 525, column: 1, scope: !995)
!1009 = distinct !DISubprogram(name: "get_memory_ptr_for_runtime", scope: !3, file: !3, line: 528, type: !1010, scopeLine: 528, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1012)
!1010 = !DISubroutineType(types: !1011)
!1011 = !{!29, !7, !7}
!1012 = !{!1013, !1014}
!1013 = !DILocalVariable(name: "off", arg: 1, scope: !1009, file: !3, line: 528, type: !7)
!1014 = !DILocalVariable(name: "bounds", arg: 2, scope: !1009, file: !3, line: 528, type: !7)
!1015 = !DILocation(line: 0, scope: !1009)
!1016 = !DILocation(line: 529, column: 44, scope: !1017)
!1017 = distinct !DILexicalBlock(scope: !1009, file: !3, line: 529, column: 9)
!1018 = !DILocation(line: 529, column: 30, scope: !1017)
!1019 = !DILocation(line: 529, column: 9, scope: !1009)
!1020 = !{!"branch_weights", i32 1, i32 2000}
!1021 = !DILocation(line: 0, scope: !105, inlinedAt: !1022)
!1022 = distinct !DILocation(line: 530, column: 9, scope: !1023)
!1023 = distinct !DILexicalBlock(scope: !1017, file: !3, line: 529, column: 62)
!1024 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1022)
!1025 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1022)
!1026 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1022)
!1027 = !DILocation(line: 0, scope: !527, inlinedAt: !1028)
!1028 = distinct !DILocation(line: 533, column: 12, scope: !1009)
!1029 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !1028)
!1030 = !DILocation(line: 533, column: 5, scope: !1009)
!1031 = distinct !DISubprogram(name: "expand_memory", scope: !3, file: !3, line: 539, type: !102, scopeLine: 539, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1032 = !DILocation(line: 0, scope: !105, inlinedAt: !1033)
!1033 = distinct !DILocation(line: 541, column: 5, scope: !1031)
!1034 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1033)
!1035 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1033)
!1036 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1033)
!1037 = distinct !DISubprogram(name: "get_function_from_table", scope: !3, file: !3, line: 553, type: !1038, scopeLine: 553, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1040)
!1038 = !DISubroutineType(types: !1039)
!1039 = !{!620, !7, !7}
!1040 = !{!1041, !1042, !1043}
!1041 = !DILocalVariable(name: "idx", arg: 1, scope: !1037, file: !3, line: 553, type: !7)
!1042 = !DILocalVariable(name: "type_id", arg: 2, scope: !1037, file: !3, line: 553, type: !7)
!1043 = !DILocalVariable(name: "f", scope: !1037, file: !3, line: 558, type: !1044)
!1044 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "table_entry", file: !3, line: 544, size: 64, elements: !1045)
!1045 = !{!1046, !1047}
!1046 = !DIDerivedType(tag: DW_TAG_member, name: "type_id", scope: !1044, file: !3, line: 545, baseType: !7, size: 32)
!1047 = !DIDerivedType(tag: DW_TAG_member, name: "func_ptr", scope: !1044, file: !3, line: 546, baseType: !6, size: 32, offset: 32)
!1048 = !DILocation(line: 0, scope: !1037)
!1049 = !DILocation(line: 554, column: 30, scope: !1050)
!1050 = distinct !DILexicalBlock(scope: !1037, file: !3, line: 554, column: 9)
!1051 = !DILocation(line: 554, column: 9, scope: !1037)
!1052 = !DILocation(line: 0, scope: !105, inlinedAt: !1053)
!1053 = distinct !DILocation(line: 555, column: 9, scope: !1054)
!1054 = distinct !DILexicalBlock(scope: !1050, file: !3, line: 554, column: 54)
!1055 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1053)
!1056 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1053)
!1057 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1053)
!1058 = !DILocation(line: 558, column: 28, scope: !1037)
!1059 = !DILocation(line: 560, column: 36, scope: !1060)
!1060 = distinct !DILexicalBlock(scope: !1037, file: !3, line: 560, column: 9)
!1061 = !DILocation(line: 560, column: 50, scope: !1060)
!1062 = !DILocation(line: 560, column: 47, scope: !1060)
!1063 = !DILocation(line: 560, column: 9, scope: !1037)
!1064 = !DILocation(line: 0, scope: !105, inlinedAt: !1065)
!1065 = distinct !DILocation(line: 561, column: 9, scope: !1066)
!1066 = distinct !DILexicalBlock(scope: !1060, file: !3, line: 560, column: 71)
!1067 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1065)
!1068 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1065)
!1069 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1065)
!1070 = !DILocation(line: 564, column: 5, scope: !1037)
!1071 = distinct !DISubprogram(name: "add_function_to_table", scope: !3, file: !3, line: 567, type: !1072, scopeLine: 567, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1074)
!1072 = !DISubroutineType(types: !1073)
!1073 = !{null, !7, !7, !6}
!1074 = !{!1075, !1076, !1077}
!1075 = !DILocalVariable(name: "idx", arg: 1, scope: !1071, file: !3, line: 567, type: !7)
!1076 = !DILocalVariable(name: "type_id", arg: 2, scope: !1071, file: !3, line: 567, type: !7)
!1077 = !DILocalVariable(name: "func_ptr", arg: 3, scope: !1071, file: !3, line: 567, type: !6)
!1078 = !DILocation(line: 0, scope: !1071)
!1079 = !DILocation(line: 568, column: 30, scope: !1080)
!1080 = distinct !DILexicalBlock(scope: !1071, file: !3, line: 568, column: 9)
!1081 = !DILocation(line: 568, column: 9, scope: !1071)
!1082 = !DILocation(line: 0, scope: !105, inlinedAt: !1083)
!1083 = distinct !DILocation(line: 569, column: 9, scope: !1084)
!1084 = distinct !DILexicalBlock(scope: !1080, file: !3, line: 568, column: 54)
!1085 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1083)
!1086 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1083)
!1087 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1083)
!1088 = !DILocation(line: 572, column: 18, scope: !1071)
!1089 = !DILocation(line: 572, column: 26, scope: !1071)
!1090 = !{!1091, !113, i64 0}
!1091 = !{!"table_entry", !113, i64 0, !92, i64 4}
!1092 = !DILocation(line: 573, column: 18, scope: !1071)
!1093 = !DILocation(line: 573, column: 27, scope: !1071)
!1094 = !{!1091, !92, i64 4}
!1095 = !DILocation(line: 574, column: 1, scope: !1071)
!1096 = distinct !DISubprogram(name: "clear_table", scope: !3, file: !3, line: 576, type: !102, scopeLine: 576, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1097 = !DILocation(line: 577, column: 5, scope: !1096)
!1098 = !DILocation(line: 578, column: 1, scope: !1096)
!1099 = !DILocation(line: 0, scope: !105)
!1100 = !DILocation(line: 666, column: 13, scope: !105)
!1101 = !DILocation(line: 665, column: 5, scope: !105)
!1102 = !DILocation(line: 667, column: 5, scope: !105)
!1103 = !DILocation(line: 0, scope: !804)
!1104 = !DILocation(line: 677, column: 13, scope: !804)
!1105 = !DILocation(line: 676, column: 12, scope: !804)
!1106 = !DILocation(line: 676, column: 5, scope: !804)
!1107 = distinct !DISubprogram(name: "populate_table", scope: !3, file: !3, line: 598, type: !102, scopeLine: 598, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1108 = !DILocation(line: 598, column: 50, scope: !1107)
!1109 = distinct !DISubprogram(name: "populate_globals", scope: !3, file: !3, line: 599, type: !102, scopeLine: 599, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1110 = !DILocation(line: 599, column: 52, scope: !1109)
!1111 = distinct !DISubprogram(name: "populate_memory", scope: !3, file: !3, line: 600, type: !102, scopeLine: 600, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1112 = !DILocation(line: 600, column: 51, scope: !1111)
!1113 = distinct !DISubprogram(name: "wasmf___wasm_call_ctors", scope: !3, file: !3, line: 601, type: !102, scopeLine: 601, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !4)
!1114 = !DILocation(line: 601, column: 59, scope: !1113)
!1115 = distinct !DISubprogram(name: "__box_push", scope: !3, file: !3, line: 606, type: !1116, scopeLine: 606, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1118)
!1116 = !DISubroutineType(types: !1117)
!1117 = !{!6, !55}
!1118 = !{!1119, !1120}
!1119 = !DILocalVariable(name: "size", arg: 1, scope: !1115, file: !3, line: 606, type: !55)
!1120 = !DILocalVariable(name: "psp", scope: !1115, file: !3, line: 609, type: !29)
!1121 = !DILocation(line: 0, scope: !1115)
!1122 = !DILocation(line: 609, column: 20, scope: !1115)
!1123 = !DILocation(line: 610, column: 13, scope: !1124)
!1124 = distinct !DILexicalBlock(scope: !1115, file: !3, line: 610, column: 9)
!1125 = !DILocation(line: 610, column: 20, scope: !1124)
!1126 = !DILocation(line: 610, column: 9, scope: !1115)
!1127 = !DILocation(line: 614, column: 18, scope: !1115)
!1128 = !DILocation(line: 615, column: 5, scope: !1115)
!1129 = !DILocation(line: 616, column: 1, scope: !1115)
!1130 = distinct !DISubprogram(name: "__box_pop", scope: !3, file: !3, line: 618, type: !1131, scopeLine: 618, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1133)
!1131 = !DISubroutineType(types: !1132)
!1132 = !{null, !55}
!1133 = !{!1134}
!1134 = !DILocalVariable(name: "size", arg: 1, scope: !1130, file: !3, line: 618, type: !55)
!1135 = !DILocation(line: 0, scope: !1130)
!1136 = !DILocation(line: 619, column: 26, scope: !1137)
!1137 = distinct !DILexicalBlock(scope: !1130, file: !3, line: 619, column: 9)
!1138 = !DILocation(line: 619, column: 39, scope: !1137)
!1139 = !DILocation(line: 619, column: 46, scope: !1137)
!1140 = !DILocation(line: 619, column: 9, scope: !1130)
!1141 = !DILocation(line: 0, scope: !105, inlinedAt: !1142)
!1142 = distinct !DILocation(line: 620, column: 9, scope: !1143)
!1143 = distinct !DILexicalBlock(scope: !1137, file: !3, line: 619, column: 73)
!1144 = !DILocation(line: 666, column: 13, scope: !105, inlinedAt: !1142)
!1145 = !DILocation(line: 665, column: 5, scope: !105, inlinedAt: !1142)
!1146 = !DILocation(line: 667, column: 5, scope: !105, inlinedAt: !1142)
!1147 = !DILocation(line: 622, column: 18, scope: !1130)
!1148 = !DILocation(line: 623, column: 1, scope: !1130)
!1149 = distinct !DISubprogram(name: "__box_init", scope: !3, file: !3, line: 628, type: !1150, scopeLine: 628, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition | DISPFlagOptimized, unit: !2, retainedNodes: !1152)
!1150 = !DISubroutineType(types: !1151)
!1151 = !{!16, !73}
!1152 = !{!1153, !1154, !1155, !1158}
!1153 = !DILocalVariable(name: "importjumptable", arg: 1, scope: !1149, file: !3, line: 628, type: !73)
!1154 = !DILocalVariable(name: "s", scope: !1149, file: !3, line: 633, type: !73)
!1155 = !DILocalVariable(name: "d", scope: !1156, file: !3, line: 634, type: !1157)
!1156 = distinct !DILexicalBlock(scope: !1149, file: !3, line: 634, column: 5)
!1157 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !7, size: 32)
!1158 = !DILocalVariable(name: "d", scope: !1159, file: !3, line: 641, type: !1157)
!1159 = distinct !DILexicalBlock(scope: !1149, file: !3, line: 641, column: 5)
!1160 = !DILocation(line: 0, scope: !1149)
!1161 = !DILocation(line: 0, scope: !1156)
!1162 = !DILocation(line: 634, column: 10, scope: !1156)
!1163 = !DILocation(line: 634, column: 41, scope: !1164)
!1164 = distinct !DILexicalBlock(scope: !1156, file: !3, line: 634, column: 5)
!1165 = !DILocation(line: 634, column: 5, scope: !1156)
!1166 = !DILocation(line: 635, column: 16, scope: !1167)
!1167 = distinct !DILexicalBlock(scope: !1164, file: !3, line: 634, column: 61)
!1168 = !DILocation(line: 635, column: 14, scope: !1167)
!1169 = !DILocation(line: 635, column: 12, scope: !1167)
!1170 = !DILocation(line: 634, column: 57, scope: !1164)
!1171 = !DILocation(line: 634, column: 5, scope: !1164)
!1172 = distinct !{!1172, !1165, !1173}
!1173 = !DILocation(line: 636, column: 5, scope: !1156)
!1174 = !DILocation(line: 0, scope: !1159)
!1175 = !DILocation(line: 641, column: 40, scope: !1176)
!1176 = distinct !DILexicalBlock(scope: !1159, file: !3, line: 641, column: 5)
!1177 = !DILocation(line: 641, column: 5, scope: !1159)
!1178 = !DILocation(line: 646, column: 27, scope: !1149)
!1179 = !DILocation(line: 650, column: 5, scope: !1149)
!1180 = !DILocation(line: 653, column: 5, scope: !1149)
!1181 = !DILocation(line: 654, column: 5, scope: !1149)
!1182 = !DILocation(line: 655, column: 5, scope: !1149)
!1183 = !DILocation(line: 656, column: 5, scope: !1149)
!1184 = !DILocation(line: 658, column: 5, scope: !1149)
!1185 = !DILocation(line: 642, column: 12, scope: !1186)
!1186 = distinct !DILexicalBlock(scope: !1176, file: !3, line: 641, column: 59)
!1187 = !DILocation(line: 641, column: 55, scope: !1176)
!1188 = !DILocation(line: 641, column: 5, scope: !1176)
!1189 = distinct !{!1189, !1177, !1190}
!1190 = !DILocation(line: 643, column: 5, scope: !1159)
!1191 = !DILocation(line: 0, scope: !517)
!1192 = !DILocation(line: 672, column: 13, scope: !517)
!1193 = !DILocation(line: 0, scope: !527, inlinedAt: !1194)
!1194 = distinct !DILocation(line: 672, column: 43, scope: !517)
!1195 = !DILocation(line: 447, column: 13, scope: !527, inlinedAt: !1194)
!1196 = !DILocation(line: 671, column: 12, scope: !517)
!1197 = !DILocation(line: 671, column: 5, scope: !517)

^0 = module: (path: "runtime/bb.bc", hash: (0, 0, 0, 0, 0))
^1 = gv: (name: "set_i64", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 378958320381972055
^2 = gv: (name: "__bss_end") ; guid = 646497284603553263
^3 = gv: (name: "__box_importjumptable", summaries: (variable: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 858446705940093091
^4 = gv: (name: "__table") ; guid = 1006201372372749385
^5 = gv: (name: "__libc_init_array") ; guid = 1317725527254348321
^6 = gv: (name: "get_i64", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 1383644484408881865
^7 = gv: (name: "get_function_from_table", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 19, refs: (^3, ^4)))) ; guid = 1511080965932565765
^8 = gv: (name: "_impure_ptr") ; guid = 2167626441343115666
^9 = gv: (name: "__box_write", summaries: (alias: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), aliasee: ^75))) ; guid = 3020744946666114155
^10 = gv: (name: "env___box_abort", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 4, refs: (^3)))) ; guid = 3346292192036212222
^11 = gv: (name: "llvm.lifetime.start.p0i8") ; guid = 3657761528566682672
^12 = gv: (name: "clear_table", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 2, calls: ((callee: ^66)), refs: (^4)))) ; guid = 3736970394882440277
^13 = gv: (name: "__wrap_vprintf", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 2, calls: ((callee: ^70)), refs: (^61)))) ; guid = 4166234784030039815
^14 = gv: (name: "__data_start") ; guid = 4360641302552284845
^15 = gv: (name: "set_i8", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 4, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 4495612517479028786
^16 = gv: (name: "__wrap_exit", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 7, refs: (^3)))) ; guid = 4628101967814496647
^17 = gv: (name: "_sbrk", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 13, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^33, ^36, ^57)))) ; guid = 4802499476880464248
^18 = gv: (name: "wasmf_mandlebrot") ; guid = 5019455901826390816
^19 = gv: (name: "get_memory_ptr_for_runtime", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 9, refs: (^3, ^23)))) ; guid = 5056148036396267458
^20 = gv: (name: "__wrap_fprintf", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 11, calls: ((callee: ^34))))) ; guid = 5076854967523987360
^21 = gv: (name: "__memory_end") ; guid = 5877127170826197044
^22 = gv: (name: "__data_init_start") ; guid = 6163802939975072960
^23 = gv: (name: "__memory") ; guid = 6277224170014865770
^24 = gv: (name: "abort_", summaries: (alias: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), aliasee: ^69))) ; guid = 6427229740669418229
^25 = gv: (name: "__box_init", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 23, calls: ((callee: ^5), (callee: ^76), (callee: ^27), (callee: ^37), (callee: ^51)), refs: (^22, ^14, ^45, ^78, ^2, ^3)))) ; guid = 7051180300319805944
^26 = gv: (name: "set_i16", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 7116226033887721171
^27 = gv: (name: "populate_globals", summaries: (function: (module: ^0, flags: (linkage: weak, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 1))) ; guid = 7164771068321562362
^28 = gv: (name: "printf") ; guid = 7383291119112528047
^29 = gv: (name: "llvm.dbg.value") ; guid = 7457163675545648777
^30 = gv: (name: "set_f32", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 8189668675583512826
^31 = gv: (name: "__box_pop", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 11, refs: (^54, ^50, ^3)))) ; guid = 8230165130662717208
^32 = gv: (name: "__wrap_fflush", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 11, refs: (^8, ^3)))) ; guid = 8920810857904562262
^33 = gv: (name: "__heap_brk", summaries: (variable: (module: ^0, flags: (linkage: internal, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 9528716227875715425
^34 = gv: (name: "__wrap_vfprintf", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 7, calls: ((callee: ^70)), refs: (^8, ^61)))) ; guid = 9722805272664717158
^35 = gv: (name: ".str", summaries: (variable: (module: ^0, flags: (linkage: private, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 9725617872798703887
^36 = gv: (name: "__heap_start") ; guid = 10367232418299670347
^37 = gv: (name: "populate_memory", summaries: (function: (module: ^0, flags: (linkage: weak, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 1))) ; guid = 10452394794136966692
^38 = gv: (name: "get_i32", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 10510499349672270265
^39 = gv: (name: "memory_size", summaries: (variable: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 10627510693591655468
^40 = gv: (name: "_write", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 8, refs: (^3, ^23)))) ; guid = 10805526404807033828
^41 = gv: (name: "llvm.va_end") ; guid = 11022308895104422842
^42 = gv: (name: ".str.1", summaries: (variable: (module: ^0, flags: (linkage: private, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 11267196268285488374
^43 = gv: (name: "__box_exportjumptable", summaries: (variable: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1), refs: (^77, ^31, ^25, ^18)))) ; guid = 11286241738601637346
^44 = gv: (name: "get_i16", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 11292322337513080881
^45 = gv: (name: "__data_end") ; guid = 11560140790960684209
^46 = gv: (name: "strcspn") ; guid = 12087458694761576634
^47 = gv: (name: "__box_flush", summaries: (alias: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), aliasee: ^55))) ; guid = 12516454007382300490
^48 = gv: (name: "set_f64", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 12625925163420070888
^49 = gv: (name: "llvm.va_start") ; guid = 12716775641641532628
^50 = gv: (name: "__memory_start") ; guid = 12896768676300170648
^51 = gv: (name: "wasmf___wasm_call_ctors", summaries: (function: (module: ^0, flags: (linkage: weak, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 1))) ; guid = 12921007852566945244
^52 = gv: (name: "to_ptr", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 2, funcFlags: (readNone: 1, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 13028913839094668105
^53 = gv: (name: "__assert_func", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, calls: ((callee: ^28)), refs: (^35, ^3)))) ; guid = 13278251807305275416
^54 = gv: (name: "__box_datasp", summaries: (variable: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1), refs: (^50)))) ; guid = 13359975925957232372
^55 = gv: (name: "env___box_flush", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 6, refs: (^3)))) ; guid = 13519801802782349971
^56 = gv: (name: "get_f64", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 13587603513972733068
^57 = gv: (name: "__heap_end") ; guid = 13744181992187314507
^58 = gv: (name: "printf_", summaries: (alias: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), aliasee: ^63))) ; guid = 13876166193532983257
^59 = gv: (name: "llvm.lifetime.end.p0i8") ; guid = 14311549039910520616
^60 = gv: (name: "expand_memory", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 4, refs: (^3)))) ; guid = 14730295745716574707
^61 = gv: (name: "__box_vprintf_write", summaries: (function: (module: ^0, flags: (linkage: internal, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 9, refs: (^3, ^23)))) ; guid = 14842768890363546988
^62 = gv: (name: ".str.2", summaries: (variable: (module: ^0, flags: (linkage: private, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), varFlags: (readonly: 1, writeonly: 1)))) ; guid = 15082291358101205028
^63 = gv: (name: "__wrap_printf", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 11, calls: ((callee: ^13))))) ; guid = 15412568874620324162
^64 = gv: (name: "__box_abort", summaries: (alias: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), aliasee: ^10))) ; guid = 15419175374938251317
^65 = gv: (name: "llvm.used", summaries: (variable: (module: ^0, flags: (linkage: appending, notEligibleToImport: 1, live: 1, dsoLocal: 0, canAutoHide: 0), varFlags: (readonly: 0, writeonly: 0), refs: (^43, ^69, ^16, ^13, ^63, ^34, ^20, ^32)))) ; guid = 15665353970260777610
^66 = gv: (name: "memset") ; guid = 15705169369643575921
^67 = gv: (name: "get_f32", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 16452588258752307793
^68 = gv: (name: "from_ptr", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 3, funcFlags: (readNone: 1, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 16852528665685532162
^69 = gv: (name: "__wrap_abort", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 4, refs: (^3)))) ; guid = 17041823504969712620
^70 = gv: (name: "__box_cbprintf", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 327, calls: ((callee: ^46)), refs: (^42, ^62)))) ; guid = 17110691845041163705
^71 = gv: (name: "_exit", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 7, refs: (^3)))) ; guid = 17210487750076657958
^72 = gv: (name: "add_function_to_table", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 11, refs: (^3, ^4)))) ; guid = 17241295654134821023
^73 = gv: (name: "set_i32", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 5, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 17300199619787318590
^74 = gv: (name: "get_i8", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 4, funcFlags: (readNone: 0, readOnly: 1, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^23)))) ; guid = 17564930359188291791
^75 = gv: (name: "env___box_write", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 7, refs: (^3, ^23)))) ; guid = 17889148837469285001
^76 = gv: (name: "populate_table", summaries: (function: (module: ^0, flags: (linkage: weak, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 1))) ; guid = 17992154599268944399
^77 = gv: (name: "__box_push", summaries: (function: (module: ^0, flags: (linkage: external, notEligibleToImport: 1, live: 0, dsoLocal: 1, canAutoHide: 0), insts: 8, funcFlags: (readNone: 0, readOnly: 0, noRecurse: 1, returnDoesNotAlias: 0, noInline: 0), refs: (^54, ^21)))) ; guid = 18091921440092463574
^78 = gv: (name: "__bss_start") ; guid = 18125732995275483612
