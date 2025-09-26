import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
import mimetypes

logger = logging.getLogger(__name__)

class FileService:
    """ファイル読み取りサービス"""
    
    def __init__(self, base_data_dir: str = "data"):
        self.base_data_dir = Path(base_data_dir)
        self.projects_dir = self.base_data_dir / "projects"
        self.materials_dir = self.base_data_dir / "materials"
        
        # サポートするファイル拡張子
        self.supported_extensions = {'.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json'}
    
    def _read_text_file(self, file_path: Path) -> Optional[str]:
        """テキストファイルを読み取る"""
        try:
            # ファイル拡張子をチェック
            if file_path.suffix.lower() not in self.supported_extensions:
                logger.warning(f"Unsupported file extension: {file_path.suffix}")
                return None
            
            # ファイルサイズをチェック（10MB制限）
            if file_path.stat().st_size > 10 * 1024 * 1024:
                logger.warning(f"File too large: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # UTF-8で読めない場合はcp932で試す
            try:
                with open(file_path, 'r', encoding='cp932') as f:
                    return f.read()
            except UnicodeDecodeError:
                logger.error(f"Failed to decode file: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def get_project_files(self, project_name: str) -> List[Dict[str, str]]:
        """プロジェクトのファイル一覧を取得"""
        project_path = self.projects_dir / project_name
        files = []
        
        if not project_path.exists():
            logger.warning(f"Project directory does not exist: {project_path}")
            return files
        
        try:
            for file_path in project_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                    relative_path = file_path.relative_to(project_path)
                    files.append({
                        "name": str(relative_path),
                        "full_path": str(file_path),
                        "size": file_path.stat().st_size
                    })
        except Exception as e:
            logger.error(f"Error listing project files: {e}")
        
        return files
    
    def get_material_files(self, book_id: str) -> List[Dict[str, str]]:
        """資料のファイル一覧を取得"""
        material_path = self.materials_dir / book_id
        files = []
        
        if not material_path.exists():
            logger.warning(f"Material directory does not exist: {material_path}")
            return files
        
        try:
            for file_path in material_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                    relative_path = file_path.relative_to(material_path)
                    files.append({
                        "name": str(relative_path),
                        "full_path": str(file_path),
                        "size": file_path.stat().st_size
                    })
        except Exception as e:
            logger.error(f"Error listing material files: {e}")
        
        return files
    
    def read_project_files_content(self, project_name: str, selected_files: List[str] = None) -> Dict[str, str]:
        """プロジェクトのファイル内容を読み取る（シンプル版・フォールバック無し）"""
        logger.info(f"=== READ PROJECT FILES ===")
        logger.info(f"Project: {project_name}")
        logger.info(f"Selected files: {selected_files}")
        
        project_path = self.projects_dir / project_name
        content_dict = {}
        
        # プロジェクトディレクトリが存在しない場合はエラー
        if not project_path.exists():
            logger.error(f"❌ Project directory does not exist: {project_path}")
            return content_dict
        
        logger.info(f"📁 Project directory found: {project_path}")
        
        try:
            # 指定されたファイルがない場合は全てのファイルを読み込む
            if selected_files is None:
                logger.info("No files specified, reading all files")
                files_to_read = []
                for file_path in project_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                        relative_path = str(file_path.relative_to(project_path))
                        if relative_path != "project_meta.json":  # メタデータファイルは除外
                            files_to_read.append(relative_path)
                            logger.info(f"Found file: {relative_path}")
            else:
                files_to_read = selected_files
                logger.info(f"Reading specified files: {files_to_read}")
            
            # ファイルを読み取り
            for file_name in files_to_read:
                file_path = project_path / file_name
                logger.info(f"🔍 Looking for file: {file_path}")
                
                if file_path.exists() and file_path.is_file():
                    logger.info(f"✅ File found: {file_name}")
                    content = self._read_text_file(file_path)
                    if content is not None:
                        content_dict[file_name] = content
                        logger.info(f"📖 Successfully read: {file_name} ({len(content)} chars)")
                        logger.info(f"Content preview: {repr(content[:100])}...")
                    else:
                        logger.error(f"❌ Failed to read content from: {file_name}")
                else:
                    logger.error(f"❌ File not found: {file_path}")
                    
        except Exception as e:
            logger.error(f"❌ Error reading project files content: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"=== READ RESULT: {len(content_dict)} files ===")
        return content_dict
        """プロジェクトのファイル内容を読み取る"""
        project_path = self.projects_dir / project_name
        content_dict = {}
        
        # プロジェクトが存在しない場合は、sample_projectにフォールバック
        if not project_path.exists():
            logger.warning(f"Project directory does not exist: {project_path}, trying sample_project")
            fallback_path = self.projects_dir / "sample_project"
            if fallback_path.exists():
                project_path = fallback_path
                logger.info(f"Using fallback project: sample_project")
            else:
                logger.error(f"Both {project_name} and sample_project directories do not exist")
                return content_dict
        
        try:
            # 指定されたファイルがない場合は全てのファイルを読み込む
            if selected_files is None:
                files_to_read = []
                for file_path in project_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                        relative_path = str(file_path.relative_to(project_path))
                        files_to_read.append(relative_path)
            else:
                files_to_read = selected_files
                
                # ファイル名の正規化は無効化（実際のファイル名をそのまま使用）
                # 実際に存在するファイルを優先し、存在しない場合のみフォールバック
                files_to_read = selected_files
            
            for file_name in files_to_read:
                file_path = project_path / file_name
                logger.info(f"Looking for file: {file_path} (exists: {file_path.exists()})")
                
                if file_path.exists() and file_path.is_file():
                    content = self._read_text_file(file_path)
                    if content is not None:
                        content_dict[file_name] = content
                        logger.info(f"Successfully read file: {file_name} ({len(content)} chars)")
                else:
                    logger.warning(f"File not found: {file_path}")
                    
                    # 個別ファイルが見つからない場合、sample_projectから同名ファイルを探す
                    fallback_path = self.projects_dir / "sample_project" / file_name
                    if fallback_path.exists():
                        logger.info(f"Using fallback file: {fallback_path}")
                        content = self._read_text_file(fallback_path)
                        if content is not None:
                            content_dict[file_name] = content
                            logger.info(f"Successfully read fallback file: {file_name}")
                    else:
                        logger.error(f"Neither original nor fallback file found for: {file_name}")
                        
        except Exception as e:
            logger.error(f"Error reading project files content: {e}")
        
        return content_dict
    
    def read_material_files_content(self, book_id: str, selected_files: List[str] = None) -> Dict[str, str]:
        """資料のファイル内容を読み取る"""
        material_path = self.materials_dir / book_id
        content_dict = {}
        
        # 資料ディレクトリが存在しない場合は、sample_bookにフォールバック
        if not material_path.exists():
            logger.warning(f"Material directory does not exist: {material_path}, trying sample_book")
            fallback_path = self.materials_dir / "sample_book"
            if fallback_path.exists():
                material_path = fallback_path
                logger.info(f"Using fallback material: sample_book")
            else:
                logger.error(f"Both {book_id} and sample_book directories do not exist")
                return content_dict
        
        try:
            # 指定されたファイルがない場合は全てのファイルを読み込む
            if selected_files is None:
                files_to_read = []
                for file_path in material_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                        relative_path = str(file_path.relative_to(material_path))
                        files_to_read.append(relative_path)
            else:
                files_to_read = selected_files
            
            for file_name in files_to_read:
                file_path = material_path / file_name
                if file_path.exists() and file_path.is_file():
                    content = self._read_text_file(file_path)
                    if content is not None:
                        content_dict[file_name] = content
                        
        except Exception as e:
            logger.error(f"Error reading material files content: {e}")
        
        return content_dict
    
    def format_files_for_context(self, files_content: Dict[str, str]) -> str:
        """ファイル内容をコンテキスト用にフォーマット"""
        if not files_content:
            return ""
        
        formatted_content = []
        formatted_content.append("=== 参照ファイル ===")
        
        for filename, content in files_content.items():
            formatted_content.append(f"\n--- ファイル: {filename} ---")
            # 内容が長すぎる場合は制限する（1ファイルあたり最大5000文字）
            if len(content) > 5000:
                formatted_content.append(content[:5000] + "\n... (ファイルが長いため省略されました)")
            else:
                formatted_content.append(content)
            formatted_content.append("--- ファイル終了 ---")
        
        formatted_content.append("=== 参照ファイル終了 ===\n")
        return "\n".join(formatted_content)


# シングルトンインスタンス
_file_service = None

def get_file_service() -> FileService:
    """FileServiceのシングルトンインスタンスを取得"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
