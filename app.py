import os
import os.path as osp
import sys
import shutil
import tempfile
import re
import atexit
import signal
from datetime import datetime

# 確保從專案根目錄執行
ROOT = osp.dirname(osp.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, osp.join(ROOT, 'inference', 'scripts'))
sys.path.insert(0, osp.join(ROOT, 'common'))

os.environ['OPENBLAS_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'
os.environ['OMP_NUM_THREADS'] = '8'
os.environ['HF_HOME'] = osp.join(ROOT, 'models')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='huggingface_hub')

print('Loading PyTorch...', end='', flush=True)
import torch
print(f'        done (CUDA: {torch.cuda.is_available()})')

print('Loading Gradio...', end='', flush=True)
import gradio as gr
print('         done')

from PIL import Image
import numpy as np

print('Loading inference modules...', end='', flush=True)
from utils.inference_utils import apply_layerdiff, apply_marigold, further_extr
from utils.torch_utils import seed_everything
print(' done')

REPO_LAYERDIFF = 'layerdifforg/seethroughv0.0.2_layerdiff3d'
REPO_DEPTH = '24yearsold/seethroughv0.0.1_marigold'
SAVE_DIR = osp.join(ROOT, 'workspace', 'layerdiff_output')

# ── i18n ──────────────────────────────────────────────
LANG = {
    'English': {
        'title': '# See-through: Single-image Layer Decomposition for Anime Characters',
        'desc': 'Upload an anime character illustration to decompose it into fully-inpainted semantic layers with depth ordering, exported as a layered PSD file.',
        'image_input': 'Input Image',
        'settings': 'Settings',
        'seed': 'Random Seed',
        'seed_info': 'Different seeds produce different decomposition results. Default: 42',
        'resolution': 'Resolution',
        'resolution_info': 'Higher = better quality but slower and more VRAM. Image is center-padded to square. Default: 1280',
        'steps': 'Inference Steps',
        'steps_info': 'Denoising steps. More = better quality but slower. Not recommended to change. Default: 30',
        'tblr': 'Left/Right Split (tblr)',
        'tblr_info': 'Split gloves, eyes, ears, etc. into separate left/right layers. Default: OFF',
        'cache_tag_embeds': 'Cache Tag Embeddings',
        'cache_tag_embeds_info': 'Pre-compute text embeddings and unload text encoders, saves ~2 GB VRAM with zero speed penalty. Default: ON',
        'group_offload': 'Group Offload (Low VRAM)',
        'group_offload_info': 'Move model blocks on/off GPU as needed. Drastically reduces VRAM but 2-3x slower. For GPUs with 8-10 GB VRAM. Default: OFF',
        'depth_same': 'Depth resolution same as layers',
        'depth_same_info': 'Uncheck to set a custom depth inference resolution. Default: -1 (same as layers)',
        'depth_resolution': 'Depth Resolution',
        'depth_resolution_info': 'Lower values save VRAM with slightly reduced depth accuracy. Default: 768 (model training resolution)',
        'run': 'Start Processing',
        'status': 'Status',
        'psd': 'Download PSD File',
        'preview': 'Layer Preview',
        'error_no_image': 'Please upload an image first',
        'progress_layerdiff': 'Running LayerDiff layer decomposition...',
        'progress_marigold': 'Running Marigold depth estimation...',
        'progress_psd': 'Compositing PSD layers...',
        'progress_done': 'Done!',
        'status_done': 'Done! Output directory: ',
    },
    '中文': {
        'title': '# See-through：動漫角色單圖圖層分解',
        'desc': '上傳一張動漫角色插圖，自動分解為完整修補的語義圖層並依深度排序，匯出為多圖層 PSD 檔案。',
        'image_input': '輸入圖片',
        'settings': '設定',
        'seed': '隨機種子',
        'seed_info': '不同的種子會產生不同的分解結果。預設：42',
        'resolution': '解析度',
        'resolution_info': '越高品質越好，但越慢且需要更多 VRAM。圖片會自動填充為正方形。預設：1280',
        'steps': '推理步數',
        'steps_info': '去噪步數，越多品質越好但越慢，不建議更動。預設：30',
        'tblr': '左右分割 (tblr)',
        'tblr_info': '將手套、眼睛、耳朵等部位分成左右兩個圖層。預設：關閉',
        'cache_tag_embeds': '快取 Tag Embeddings',
        'cache_tag_embeds_info': '預先計算文字嵌入並卸載文字編碼器，省約 2 GB VRAM，零速度損失。預設：開啟',
        'group_offload': 'Group Offload（低 VRAM 模式）',
        'group_offload_info': '按需移動模型區塊進出 GPU，大幅降低 VRAM 但慢 2-3 倍，適合 8-10 GB 顯卡。預設：關閉',
        'depth_same': '深度解析度與圖層相同',
        'depth_same_info': '取消勾選可自訂深度推理解析度。預設：-1（與圖層相同）',
        'depth_resolution': '深度解析度',
        'depth_resolution_info': '較低值可節省 VRAM，深度精度會略降。預設：768（模型訓練解析度）',
        'run': '開始處理',
        'status': '狀態',
        'psd': '下載 PSD 檔案',
        'preview': '圖層預覽',
        'error_no_image': '請先上傳圖片',
        'progress_layerdiff': '執行 LayerDiff 圖層分解中...',
        'progress_marigold': '執行 Marigold 深度估計中...',
        'progress_psd': '合成 PSD 圖層中...',
        'progress_done': '完成！',
        'status_done': '完成！輸出目錄：',
    },
}


def switch_language(lang):
    t = LANG[lang]
    return [
        gr.update(value=t['title']),
        gr.update(value=t['desc']),
        gr.update(label=t['image_input']),
        gr.update(label=t['settings']),
        gr.update(label=t['seed'], info=t['seed_info']),
        gr.update(label=t['resolution'], info=t['resolution_info']),
        gr.update(label=t['steps'], info=t['steps_info']),
        gr.update(label=t['tblr'], info=t['tblr_info']),
        gr.update(label=t['cache_tag_embeds'], info=t['cache_tag_embeds_info']),
        gr.update(label=t['group_offload'], info=t['group_offload_info']),
        gr.update(label=t['depth_same'], info=t['depth_same_info']),
        gr.update(label=t['depth_resolution'], info=t['depth_resolution_info']),
        gr.update(value=t['run']),
        gr.update(label=t['status']),
        gr.update(label=t['psd']),
        gr.update(label=t['preview']),
    ]


def run_pipeline(image, seed, resolution, steps, tblr_split, cache_tag_embeds, group_offload, depth_same, depth_resolution, lang, progress=gr.Progress(track_tqdm=False)):
    t = LANG[lang]
    if image is None:
        raise gr.Error(t['error_no_image'])

    os.makedirs(SAVE_DIR, exist_ok=True)

    if isinstance(image, str) and osp.isfile(image):
        raw_name = osp.splitext(osp.basename(image))[0]
    else:
        raw_name = 'image'

    safe_base = re.sub(r'[^\w\-]', '_', raw_name)[:40] or 'image'

    srcname = safe_base
    if osp.exists(osp.join(SAVE_DIR, srcname)):
        srcname = f'{safe_base}_{datetime.now().strftime("%H%M%S")}'

    tmp_path = osp.join(SAVE_DIR, srcname + '.png')
    if isinstance(image, str):
        shutil.copy2(image, tmp_path)
    else:
        Image.fromarray(image).save(tmp_path)

    depth_res = -1 if depth_same else int(depth_resolution)

    try:
        seed = int(seed)
        seed_everything(seed)

        progress(0.1, desc=t['progress_layerdiff'])
        apply_layerdiff(
            tmp_path, REPO_LAYERDIFF,
            save_dir=SAVE_DIR, seed=seed,
            resolution=int(resolution),
            num_inference_steps=int(steps),
            disable_progressbar=False,
            cache_tag_embeds=cache_tag_embeds,
            group_offload=group_offload
        )

        progress(0.6, desc=t['progress_marigold'])
        apply_marigold(
            tmp_path, REPO_DEPTH,
            save_dir=SAVE_DIR, seed=seed,
            resolution=depth_res,
            disable_progressbar=False,
            cache_tag_embeds=cache_tag_embeds,
            group_offload=group_offload
        )

        progress(0.85, desc=t['progress_psd'])
        saved = osp.join(SAVE_DIR, srcname)
        further_extr(saved, rotate=False, save_to_psd=True, tblr_split=tblr_split)

        psd_path = osp.join(SAVE_DIR, f'{srcname}.psd')

        preview_imgs = []
        exclude = {'src_img.png', 'src_head.png', 'reconstruction.png'}
        optimized_dir = osp.join(saved, 'optimized')
        # Use optimized/ only if it has PNGs, otherwise fall back to saved/
        optimized_pngs = [f for f in os.listdir(optimized_dir) if f.endswith('.png')] if osp.isdir(optimized_dir) else []
        preview_dir = optimized_dir if optimized_pngs else saved
        if osp.isdir(preview_dir):
            layer_files = sorted([
                osp.join(preview_dir, f) for f in os.listdir(preview_dir)
                if f.endswith('.png')
                and not f.endswith('_depth.png')
                and f not in exclude
            ])
            for lf in layer_files:
                try:
                    img = Image.open(lf).convert('RGBA')
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    preview_imgs.append((bg, osp.basename(lf).replace('.png', '')))
                except Exception:
                    pass

        progress(1.0, desc=t['progress_done'])

        status = t['status_done'] + saved
        return (
            psd_path if osp.exists(psd_path) else None,
            preview_imgs,
            status,
        )

    finally:
        if osp.exists(tmp_path):
            os.unlink(tmp_path)


with gr.Blocks(title='See-through') as demo:
    lang_selector = gr.Radio(
        choices=['English', '中文'],
        value='English',
        label='Language / 語言',
        interactive=True,
    )

    title_md = gr.Markdown('# See-through: Single-image Layer Decomposition for Anime Characters')
    desc_md = gr.Markdown('Upload an anime character illustration to decompose it into fully-inpainted semantic layers with depth ordering, exported as a layered PSD file.')

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label='Input Image',
                type='filepath',
                height=400
            )
            with gr.Accordion('Settings', open=True) as settings_acc:
                seed_input = gr.Number(
                    label='Random Seed', value=42, precision=0,
                    info='Different seeds produce different decomposition results. Default: 42'
                )
                resolution_input = gr.Slider(
                    label='Resolution',
                    minimum=512, maximum=1536, step=128, value=1280,
                    info='Higher = better quality but slower and more VRAM. Image is center-padded to square. Default: 1280'
                )
                steps_input = gr.Slider(
                    label='Inference Steps',
                    minimum=1, maximum=50, step=1, value=30,
                    info='Denoising steps. More = better quality but slower. Not recommended to change. Default: 30'
                )
                tblr_input = gr.Checkbox(
                    label='Left/Right Split (tblr)',
                    value=False,
                    info='Split gloves, eyes, ears, etc. into separate left/right layers. Default: OFF'
                )
                cache_tag_embeds_input = gr.Checkbox(
                    label='Cache Tag Embeddings',
                    value=True,
                    info='Pre-compute text embeddings and unload text encoders, saves ~2 GB VRAM with zero speed penalty. Default: ON'
                )
                group_offload_input = gr.Checkbox(
                    label='Group Offload (Low VRAM)',
                    value=False,
                    info='Move model blocks on/off GPU as needed. Drastically reduces VRAM but 2-3x slower. For GPUs with 8-10 GB VRAM. Default: OFF'
                )
                depth_same_input = gr.Checkbox(
                    label='Depth resolution same as layers',
                    value=True,
                    info='Uncheck to set a custom depth inference resolution. Default: -1 (same as layers)'
                )
                depth_resolution_input = gr.Slider(
                    label='Depth Resolution',
                    minimum=512, maximum=1536, step=128, value=768,
                    visible=False,
                    info='Lower values save VRAM with slightly reduced depth accuracy. Default: 768 (model training resolution)'
                )
                depth_same_input.change(
                    fn=lambda x: gr.update(visible=not x),
                    inputs=[depth_same_input],
                    outputs=[depth_resolution_input],
                    show_progress='hidden'
                )
            run_btn = gr.Button('Start Processing', variant='primary', size='lg')

        with gr.Column(scale=1):
            status_output = gr.Textbox(label='Status', interactive=False)
            psd_output = gr.File(label='Download PSD File')
            preview_output = gr.Gallery(
                label='Layer Preview',
                columns=4,
                height=400,
                object_fit='contain'
            )

    lang_selector.change(
        fn=switch_language,
        inputs=[lang_selector],
        outputs=[
            title_md, desc_md, image_input, settings_acc,
            seed_input, resolution_input, steps_input,
            tblr_input, cache_tag_embeds_input, group_offload_input,
            depth_same_input, depth_resolution_input,
            run_btn,
            status_output, psd_output, preview_output,
        ]
    )

    run_btn.click(
        fn=run_pipeline,
        inputs=[image_input, seed_input, resolution_input, steps_input,
                tblr_input, cache_tag_embeds_input, group_offload_input,
                depth_same_input, depth_resolution_input, lang_selector],
        outputs=[psd_output, preview_output, status_output]
    )

def _cleanup(*args):
    """Release directory handles so workspace can be deleted after exit."""
    try:
        os.chdir(osp.expanduser('~'))
    except Exception:
        pass
    if args:
        sys.exit(0)

if __name__ == '__main__':
    atexit.register(_cleanup)
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)
    demo.launch(
        server_name='127.0.0.1',
        server_port=7860,
        inbrowser=True,
        share=False,
        theme=gr.themes.Soft()
    )
