@echo off
echo 修复protobuf版本兼容性问题...
echo TensorFlow需要protobuf < 3.20，但当前版本可能太高
echo.

echo 当前protobuf版本:
python -c "import google.protobuf; print(google.protobuf.__version__)" 2>nul
if errorlevel 1 (
    echo 未安装protobuf
)

echo.
echo 安装兼容版本...
pip install --upgrade "protobuf<3.20,>=3.9.2"

echo.
echo 修复完成！现在可以运行应用了。
echo 运行: python -m streamlit run app.py
pause