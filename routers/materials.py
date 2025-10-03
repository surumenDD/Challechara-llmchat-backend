from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Dict, Any
import logging
import json
import time
from pathlib import Path

from models.schemas import Material, MaterialUploadRequest, ChatRequest, ChatMessage, ChatResponse
from services.gemini_service import get_gemini_service
from services.file_service import get_file_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 資料保存用のディレクトリ
MATERIALS_DIR = Path("./data/materials")
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/materials/upload")
async def upload_material(
    book_id: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...)
):
    """資料ファイルのアップロード"""
    try:
        logger.info(f"Uploading material for book {book_id}: {title}")
        file_service = get_file_service()
        
        # ファイル内容を読み取り
        content = await file.read()
        
        # テキストファイルの場合、内容を文字列として保存
        if file.content_type and file.content_type.startswith('text/'):
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('shift_jis')
                except UnicodeDecodeError:
                    text_content = content.decode('utf-8', errors='replace')
        else:
            # バイナリファイルの場合、ファイル名のみ保存（実際の実装では適切な処理が必要）
            text_content = f"[Binary file: {file.filename}]"
        
        # ファイル名からタイトルを決定（重複があれば自動調整）
        filename = file.filename or title
        if not filename.endswith('.txt'):
            filename += '.txt'
            
        # 資料ディレクトリに保存
        saved_path = file_service.save_material_file(book_id, filename, text_content)
        
        # 資料オブジェクトを作成
        material = Material(
            id=f"material-{int(time.time())}-{abs(hash(title)) % 10000}",
            title=filename,
            content=text_content,
            file_type=file.content_type or 'text/plain',
            size=len(content),
            created_at=int(time.time() * 1000)
        )
        
        logger.info(f"Material uploaded successfully to: {saved_path}")
        
        return {
            "success": True,
            "material": material,
            "message": "資料が正常にアップロードされました"
        }
        
    except Exception as e:
        logger.error(f"Error uploading material: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "material_upload_error",
                "message": "資料のアップロードでエラーが発生しました",
                "details": str(e)
            }
        )

@router.get("/materials/{book_id}")
async def get_materials(book_id: str) -> List[Material]:
    """指定されたブックの資料一覧を取得"""
    try:
        logger.info(f"Getting materials for book: {book_id}")
        file_service = get_file_service()
        
        # ファイルシステムから資料一覧を取得
        material_files = file_service.list_material_files(book_id)
        
        materials = []
        for filename in material_files:
            try:
                content = file_service.read_material_file_content(book_id, filename)
                material = Material(
                    id=f"material-{abs(hash(filename)) % 100000}",
                    title=filename,
                    content=content or "",
                    file_type="text/plain",
                    size=len(content) if content else 0,
                    created_at=int(time.time() * 1000)
                )
                materials.append(material)
            except Exception as file_error:
                logger.warning(f"Error reading material file {filename}: {file_error}")
        
        logger.info(f"Found {len(materials)} materials for book {book_id}")
        return materials
        
    except Exception as e:
        logger.error(f"Error getting materials: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "get_materials_error",
                "message": "資料の取得でエラーが発生しました",
                "details": str(e)
            }
        )

@router.delete("/materials/{book_id}/{material_id}")
async def delete_material(book_id: str, material_id: str):
    """資料を削除"""
    try:
        logger.info(f"Deleting material {material_id} from book {book_id}")
        file_service = get_file_service()
        
        # material_idからファイル名を特定（簡易的な実装）
        material_files = file_service.list_material_files(book_id)
        filename_to_delete = None
        
        for filename in material_files:
            # material_idとファイル名のハッシュを照合
            file_id = f"material-{abs(hash(filename)) % 100000}"
            if file_id == material_id:
                filename_to_delete = filename
                break
        
        if not filename_to_delete:
            raise HTTPException(
                status_code=404,
                detail="指定された資料が見つかりません"
            )
        
        # ファイルを削除
        file_service.delete_material_file(book_id, filename_to_delete)
        
        logger.info(f"Material {material_id} deleted successfully")
        
        return {
            "success": True,
            "message": "資料が削除されました"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "delete_material_error",
                "message": "資料の削除でエラーが発生しました",
                "details": str(e)
            }
        )

@router.post("/materials/{book_id}/bulk-upload")
async def bulk_upload_materials(
    book_id: str,
    files: List[UploadFile] = File(...)
):
    """複数資料の一括アップロード"""
    try:
        logger.info(f"Bulk uploading {len(files)} materials for book {book_id}")
        file_service = get_file_service()
        
        uploaded_materials = []
        errors = []
        
        for file in files:
            try:
                # 個別ファイルのアップロード処理
                content = await file.read()
                
                if file.content_type and file.content_type.startswith('text/'):
                    try:
                        text_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        text_content = content.decode('utf-8', errors='replace')
                else:
                    text_content = f"[Binary file: {file.filename}]"
                
                filename = file.filename or "Unnamed file"
                if not filename.endswith('.txt'):
                    filename += '.txt'
                
                # ファイルを保存
                saved_path = file_service.save_material_file(book_id, filename, text_content)
                
                material = Material(
                    id=f"material-{int(time.time())}-{abs(hash(filename)) % 10000}",
                    title=filename,
                    content=text_content,
                    file_type=file.content_type or 'text/plain',
                    size=len(content),
                    created_at=int(time.time() * 1000)
                )
                
                uploaded_materials.append(material)
                
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
        
        logger.info(f"Bulk upload completed: {len(uploaded_materials)} success, {len(errors)} errors")
        
        return {
            "success": True,
            "uploaded_count": len(uploaded_materials),
            "error_count": len(errors),
            "materials": uploaded_materials,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "bulk_upload_error",
                "message": "一括アップロードでエラーが発生しました",
                "details": str(e)
            }
        )