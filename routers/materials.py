from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Dict, Any
import logging
import json
import time
from pathlib import Path

from models.schemas import Material, MaterialUploadRequest, ChatRequest, ChatMessage
from services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 資料保存用のディレクトリ
MATERIALS_DIR = Path("./data/materials")
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

# インメモリ資料ストレージ（本番環境ではデータベースを使用）
materials_storage: Dict[str, List[Material]] = {}

@router.post("/materials/upload")
async def upload_material(
    book_id: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...)
):
    """資料ファイルのアップロード"""
    try:
        logger.info(f"Uploading material for book {book_id}: {title}")
        
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
        
        # 資料オブジェクトを作成
        material = Material(
            id=f"material-{int(time.time())}-{abs(hash(title)) % 10000}",
            title=title,
            content=text_content,
            file_type=file.content_type,
            size=len(content),
            created_at=int(time.time() * 1000)
        )
        
        # ストレージに保存
        if book_id not in materials_storage:
            materials_storage[book_id] = []
        materials_storage[book_id].append(material)
        
        # ファイルをディスクに保存（オプション）
        file_path = MATERIALS_DIR / f"{material.id}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Material uploaded successfully: {material.id}")
        
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
        
        materials = materials_storage.get(book_id, [])
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
        
        if book_id not in materials_storage:
            raise HTTPException(
                status_code=404,
                detail="指定されたブックに資料が見つかりません"
            )
        
        materials = materials_storage[book_id]
        original_count = len(materials)
        
        # 資料を削除
        materials_storage[book_id] = [
            m for m in materials if m.id != material_id
        ]
        
        if len(materials_storage[book_id]) == original_count:
            raise HTTPException(
                status_code=404,
                detail="指定された資料が見つかりません"
            )
        
        # ファイルも削除（ファイルが存在する場合）
        try:
            for material in materials:
                if material.id == material_id:
                    # 実際のファイル削除はここで行う（実装は省略）
                    break
        except Exception as e:
            logger.warning(f"Could not delete physical file: {e}")
        
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
                
                material = Material(
                    id=f"material-{int(time.time())}-{abs(hash(file.filename or 'unnamed')) % 10000}",
                    title=file.filename or "Unnamed file",
                    content=text_content,
                    file_type=file.content_type,
                    size=len(content),
                    created_at=int(time.time() * 1000)
                )
                
                if book_id not in materials_storage:
                    materials_storage[book_id] = []
                materials_storage[book_id].append(material)
                
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

@router.post("/chat/materials")
async def materials_chat(request: ChatRequest) -> Dict[str, Any]:
    """資料・マテリアル関連チャット"""
    try:
        logger.info(f"Materials chat request with {len(request.messages)} messages")
        logger.info(f"Sources: {request.sources}")
        
        # Geminiサービスを使用してレスポンスを生成
        gemini_service = get_gemini_service()
        response_message = await gemini_service.generate_response(
            request=request,
            chat_type="material"
        )
        
        return {"message": response_message}
        
    except Exception as e:
        logger.error(f"Error in materials chat: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "materials_chat_error", 
                "message": "資料チャットでエラーが発生しました",
                "details": str(e)
            }
        )