//! 内置「同目录依赖文件」（2026-09-20 新增）
//!
//! ## 为什么需要
//! 原机的游戏是**从它自己所在的那个目录**按文件名读同目录文件的 —— 文件名明文写在
//! `.CBE` 里（ASCII 与 UTF-16LE 两种编码都有）。实测：
//!
//! | 游戏 | 它要的文件 |
//! |---|---|
//! | `武林外传V2.CBE` | `WpayKer42V100.CBM` + `upinfo2.dat` `downinfo2.dat` `downinfo.dat` `helpinfo.dat` `imeiInfo.dat` |
//! | `小酷V2.CBE`（酷吧） | `WpayKer42WqvgaV100.CBM` + 同样那 5 个 `*info*.dat` |
//!
//! 而线上核的虚拟文件系统初始是**空的**（`VirtualFileSystem::default()`），
//! 于是这些 `open()` 全部返回 -1 → 游戏卡在「系统库已有更新版本，是否更新」之类的提示上。
//!
//! 详见 `CBM与同目录依赖_扫描结论_20260920.md`。
//!
//! ## 命中规则
//! 只按**文件名前缀 + 扩展名**命中，不按全名 —— 因为不同游戏写的是不同的名字，
//! 而内容其实是同一份：原机目录里 `WpayKer42V100.CBM` 与 `WpayKer42WqvgaV100.CBM`
//! 的 md5 **完全相同**（`8f7d757bc82d4a56d81e58b6e87ebb2b`，75341 字节）。
//! 这正是「其实有时候就是改了个名字」那一层。
//!
//! ## ⚠️ 故意「只放原机目录里真实存在的文件」
//! `upinfo2.dat` / `downinfo2.dat` / `downinfo.dat` / `helpinfo.dat` / `imeiInfo.dat`
//! / `N6206V01.xml` 这些在原机目录里**也不存在**（游戏本来就容忍它们缺失），
//! 所以这里**不能**拿空文件去凑：「文件不存在」和「文件存在但是空的」对游戏是
//! 两种不同的分支，拿空文件顶上去可能反而把游戏带进解析垃圾数据的路。
//! 要加它们，得先有真实内容或先实测。
//!
//! ## 数据从哪来
//! 编译前由 CI 从 `https://emu.magicblue.cn/cbe/components/` 取到
//! `crates/nicaiemu-core/assets/` 下（见 `.github/workflows/nicaiemu.yml` 的
//! 「Fetch built-in component files」步骤）。

/// MTK WAP 计费组件（CBE Module）。
///
/// 头 `FE FE FE FE`（0xFE 填充的裸机代码段），内含 `WPay_Mtk` / `WINGTECH`（闻泰）
/// / `vMGetPrjCustom` / `vMGetSmsCenter` / `+8613800210500`（短信中心号）。
const WPAY_CBM: &[u8] = include_bytes!("../assets/WpayKer42V100.CBM");

/// 按路径取内置文件。
///
/// 内部自己做小写归一化，**不要求**调用方先归一化 —— 免得哪天有人在
/// `normalize_path()` 之前调它就静默漏掉（这种漏很难查）。
/// 分隔符 `/` 和 `\` 都认（游戏里两种写法都有）。
pub(crate) fn builtin_file(path: &str) -> Option<&'static [u8]> {
    let name = path
        .rsplit(|c| c == '/' || c == '\\')
        .next()
        .unwrap_or(path)
        .to_lowercase();
    if name.starts_with("wpayker") && name.ends_with(".cbm") {
        return Some(WPAY_CBM);
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_wpay_cbm_by_prefix_under_any_directory() {
        assert!(builtin_file("wpayker42v100.cbm").is_some());
        assert!(builtin_file("wpayker42wqvgav100.cbm").is_some());
        assert!(builtin_file("mb_w_qvga/wpayker42v100.cbm").is_some());
        // 大小写、反斜杠路径都要认（游戏里两种写法都有）
        assert!(builtin_file("WpayKer42V100.CBM").is_some());
        assert!(builtin_file("MB_W_QVGA\\WpayKer42V100.CBM").is_some());
    }

    #[test]
    fn does_not_match_other_names() {
        assert!(builtin_file("upinfo2.dat").is_none());
        assert!(builtin_file("downinfo.dat").is_none());
        assert!(builtin_file("n6206v01.xml").is_none());
        assert!(builtin_file("wpayker42v100.dat").is_none());
        assert!(builtin_file("wpayinnercbm_wqvga.mid").is_none());
    }

    #[test]
    fn built_in_blob_is_the_real_component() {
        let data = builtin_file("wpayker42v100.cbm").unwrap();
        assert_eq!(data.len(), 75341);
        assert_eq!(&data[..4], &[0xfe, 0xfe, 0xfe, 0xfe]);
    }
}
