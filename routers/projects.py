from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Dict, Optional
import logging
import json
import uuid
import os
from pathlib import Path
from datetime import datetime
from services.file_service import get_file_service, FileService

logger = logging.getLogger(__name__)

router = APIRouter()

# メタデータファイル名
METADATA_FILE = "project_meta.json"


def load_project_metadata(project_path: Path) -> dict:
    """プロジェクトのメタデータを読み込む"""
    metadata_file = project_path / METADATA_FILE
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading project metadata: {e}")

    # デフォルトメタデータ
    return {
        "id": project_path.name,
        "title": project_path.name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "file_count": 0
    }


def save_project_metadata(project_path: Path, metadata: dict):
    """プロジェクトのメタデータを保存する"""
    metadata_file = project_path / METADATA_FILE
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving project metadata: {e}")


@router.get("/projects")
async def list_projects(
    file_service: FileService = Depends(get_file_service)
):
    """利用可能なプロジェクト一覧を取得"""
    try:
        projects = []
        projects_dir = file_service.projects_dir

        if projects_dir.exists():
            for project_path in projects_dir.iterdir():
                if project_path.is_dir() and not project_path.name.startswith('.'):
                    # メタデータを読み込み
                    metadata = load_project_metadata(project_path)

                    # ファイル数をカウント
                    file_count = 0
                    for file_path in project_path.glob("*"):
                        if file_path.is_file() and file_path.name != METADATA_FILE:
                            if file_path.suffix.lower() in {'.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json'}:
                                file_count += 1

                    metadata["file_count"] = file_count
                    projects.append(metadata)

        # 更新日時順でソート
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return {"projects": projects}

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(
            status_code=500,
            detail="プロジェクト一覧の取得に失敗しました"
        )


@router.get("/projects/{project_id}")
async def get_project_detail(
    project_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """指定されたプロジェクトの詳細情報とファイル一覧を取得"""
    try:
        logger.info(f"=== GET PROJECT DETAIL ===")
        logger.info(f"Project ID: {project_id}")

        project_path = file_service.projects_dir / project_id
        if not project_path.exists():
            logger.warning(f"Project not found: {project_path}")
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        # プロジェクトメタデータを読み込み
        metadata = load_project_metadata(project_path)
        logger.info(f"Loaded metadata: {metadata}")

        # ファイル一覧を取得
        files = []
        if project_path.exists() and project_path.is_dir():
            for file_path in project_path.glob("*.txt"):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        stat = file_path.stat()
                        files.append({
                            "id": f"file-{file_path.stem}-{int(stat.st_mtime * 1000)}",
                            "title": file_path.name,
                            "content": content,
                            "createdAt": int(stat.st_ctime * 1000),
                            "updatedAt": int(stat.st_mtime * 1000)
                        })
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")

        # ファイル数を更新
        metadata["file_count"] = len(files)
        
        # アクティブファイルIDを設定（最初のファイルまたはNone）
        active_file_id = files[0]["id"] if files else None

        result = {
            "id": metadata["id"],
            "title": metadata["title"],
            "coverEmoji": metadata.get("coverEmoji", "📚"),
            "createdAt": metadata.get("created_at"),
            "updatedAt": metadata.get("updated_at"),
            "file_count": len(files),
            "files": files,
            "activeFileId": active_file_id,
            "sourceCount": 0,
            "archived": False
        }

        logger.info(f"Project detail result: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project detail: {e}")
        raise HTTPException(
            status_code=500,
            detail="プロジェクト詳細の取得に失敗しました"
        )


@router.post("/projects")
async def create_project(
    title: str = Form(...),
    id: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service)
):
    """新しいプロジェクトを作成"""
    try:
        logger.info(f"=== CREATE PROJECT REQUEST ===")
        logger.info(f"Title: {title}")
        logger.info(f"ID: {id}")
        
        # IDが指定されていない場合は生成
        project_id = id if id else f"project-{uuid.uuid4().hex[:8]}"
        logger.info(f"Final project ID: {project_id}")

        # プロジェクトディレクトリを作成
        project_dir = file_service.projects_dir / project_id
        if project_dir.exists():
            logger.warning(f"Project directory already exists: {project_dir}")
            raise HTTPException(status_code=400, detail="プロジェクトIDが既に存在します")

        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project directory: {project_dir}")

        # メタデータを保存
        metadata = {
            "id": project_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "file_count": 0
        }
        save_project_metadata(project_dir, metadata)
        logger.info(f"Saved project metadata")

        logger.info(f"=== PROJECT CREATED SUCCESSFULLY ===")

        return {
            "success": True,
            "project": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="プロジェクトの作成に失敗しました")


@router.post("/projects/{project_id}/files")
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service)
):
    """プロジェクトにファイルをアップロード"""
    try:
        # プロジェクトディレクトリの存在確認
        project_dir = file_service.projects_dir / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        # ファイル名を決定
        actual_filename = filename if filename else file.filename
        if not actual_filename:
            raise HTTPException(status_code=400, detail="ファイル名が必要です")

        # ファイル名をURLデコード
        import urllib.parse
        decoded_filename = urllib.parse.unquote(actual_filename)

        # ファイルを保存
        file_path = project_dir / decoded_filename

        content = await file.read()
        
        # テキストファイルの場合はUTF-8として扱う
        if decoded_filename.endswith(('.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json')):
            # テキストファイルとして保存
            text_content = content.decode('utf-8')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        else:
            # バイナリファイルとして保存
            with open(file_path, 'wb') as f:
                f.write(content)

        # メタデータを更新
        metadata = load_project_metadata(project_dir)
        metadata["updated_at"] = datetime.now().isoformat()
        save_project_metadata(project_dir, metadata)

        logger.info(
            f"Uploaded file to project {project_id}: {decoded_filename}")

        return {
            "success": True,
            "filename": decoded_filename,
            "size": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="ファイルのアップロードに失敗しました")


@router.put("/projects/{project_id}/files/{filename}")
async def save_project_file(
    project_id: str,
    filename: str,
    content: str = Form(...),
    file_service: FileService = Depends(get_file_service)
):
    """プロジェクトファイルの内容を保存"""
    try:
        logger.info(f"=== SAVE FILE REQUEST ===")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Content length: {len(content)} characters")
        
        # プロジェクトディレクトリを作成（存在しない場合）
        project_dir = file_service.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Project directory: {project_dir}")

        # ファイル名をURLデコード
        import urllib.parse
        decoded_filename = urllib.parse.unquote(filename)
        logger.info(f"Decoded filename: {decoded_filename}")

        # ファイルパスを構築
        file_path = project_dir / decoded_filename
        logger.info(f"File path: {file_path}")

        # UTF-8でファイルを保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 保存確認
        if file_path.exists():
            actual_size = file_path.stat().st_size
            logger.info(f"✅ File saved successfully: {actual_size} bytes")
        else:
            logger.error(f"❌ File was not saved!")
            raise Exception("File save failed")

        # メタデータを更新
        metadata = load_project_metadata(project_dir)
        metadata["updated_at"] = datetime.now().isoformat()
        save_project_metadata(project_dir, metadata)

        logger.info(f"=== SAVE FILE SUCCESS ===")

        return {
            "success": True,
            "filename": decoded_filename,
            "size": len(content.encode('utf-8')),
            "path": str(file_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file content for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました")


@router.delete("/projects/{project_id}/files/{filename}")
async def delete_project_file(
    project_id: str,
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """プロジェクトファイルを削除"""
    try:
        logger.info(f"=== DELETE FILE REQUEST ===")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Filename: {filename}")
        
        # プロジェクトディレクトリの存在確認
        project_dir = file_service.projects_dir / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        # ファイル名をURLデコード
        import urllib.parse
        decoded_filename = urllib.parse.unquote(filename)
        logger.info(f"Decoded filename: {decoded_filename}")

        # ファイルパスを構築
        file_path = project_dir / decoded_filename
        logger.info(f"File path: {file_path}")

        # ファイルが存在する場合は削除
        if file_path.exists():
            file_path.unlink()
            logger.info(f"✅ File deleted successfully: {file_path}")
        else:
            logger.warning(f"❌ File not found: {file_path}")
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")

        # メタデータを更新
        metadata = load_project_metadata(project_dir)
        metadata["updated_at"] = datetime.now().isoformat()
        save_project_metadata(project_dir, metadata)

        logger.info(f"=== DELETE FILE SUCCESS ===")

        return {
            "success": True,
            "filename": decoded_filename,
            "message": "ファイルが削除されました"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="ファイルの削除に失敗しました")


@router.put("/projects/{project_id}/files/{old_filename}/rename/{new_filename}")
async def rename_project_file(
    project_id: str,
    old_filename: str,
    new_filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """プロジェクトファイル名を変更"""
    try:
        logger.info(f"=== RENAME FILE REQUEST ===")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Old filename: {old_filename}")
        logger.info(f"New filename: {new_filename}")
        
        # プロジェクトディレクトリの存在確認
        project_dir = file_service.projects_dir / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        # ファイル名をURLデコード
        import urllib.parse
        decoded_old_filename = urllib.parse.unquote(old_filename)
        decoded_new_filename = urllib.parse.unquote(new_filename)
        logger.info(f"Decoded old filename: {decoded_old_filename}")
        logger.info(f"Decoded new filename: {decoded_new_filename}")

        # 古いファイルパスと新しいファイルパス
        old_file_path = project_dir / decoded_old_filename
        new_file_path = project_dir / decoded_new_filename
        logger.info(f"Old file path: {old_file_path}")
        logger.info(f"New file path: {new_file_path}")

        # 古いファイルが存在するか確認
        if not old_file_path.exists():
            logger.error(f"❌ Old file not found: {old_file_path}")
            raise HTTPException(status_code=404, detail="変更対象のファイルが見つかりません")

        # 新しいファイル名が既に存在するか確認
        if new_file_path.exists():
            logger.error(f"❌ New filename already exists: {new_file_path}")
            raise HTTPException(status_code=409, detail="新しいファイル名は既に使用されています")

        # ファイル名を変更（移動）
        old_file_path.rename(new_file_path)
        logger.info(f"✅ File renamed successfully: {old_file_path} -> {new_file_path}")

        # メタデータを更新
        metadata = load_project_metadata(project_dir)
        metadata["updated_at"] = datetime.now().isoformat()
        save_project_metadata(project_dir, metadata)

        logger.info(f"=== RENAME FILE SUCCESS ===")

        return {
            "success": True,
            "old_filename": decoded_old_filename,
            "new_filename": decoded_new_filename,
            "message": "ファイル名が変更されました"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error saving file content for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました")


@router.get("/projects/{project_name}/files")
async def list_project_files(
    project_name: str,
    file_service: FileService = Depends(get_file_service)
):
    """プロジェクトのファイル一覧を取得"""
    try:
        files = file_service.get_project_files(project_name)
        return {
            "project_name": project_name,
            "files": files
        }

    except Exception as e:
        logger.error(f"Error listing project files: {e}")
        raise HTTPException(
            status_code=500,
            detail="プロジェクトファイル一覧の取得に失敗しました"
        )


@router.get("/materials/{book_id}/files")
async def list_material_files(
    book_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """資料のファイル一覧を取得"""
    try:
        files = file_service.get_material_files(book_id)
        return {
            "book_id": book_id,
            "files": files
        }

    except Exception as e:
        logger.error(f"Error listing material files: {e}")
        raise HTTPException(
            status_code=500,
            detail="資料ファイル一覧の取得に失敗しました"
        )
