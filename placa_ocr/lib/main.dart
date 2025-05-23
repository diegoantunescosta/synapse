import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Placa OCR',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  File? _image;
  Uint8List? _webImage;
  String _ocrResult = "";
  bool _isSending = false;

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.camera);
    if (pickedFile != null) {
      if (kIsWeb) {
        var bytes = await pickedFile.readAsBytes();
        setState(() {
          _webImage = bytes;
          _image = null;
          _ocrResult = "";
        });
      } else {
        setState(() {
          _image = File(pickedFile.path);
          _webImage = null;
          _ocrResult = "";
        });
      }
    }
  }

  Future<void> _sendToBackend() async {
    if (_image == null && _webImage == null) return;
    setState(() { _isSending = true; });
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('https://9497-189-90-97-48.ngrok-free.app/detect-ocr/'),
    );
    if (kIsWeb && _webImage != null) {
      request.files.add(
        http.MultipartFile.fromBytes('file', _webImage!, filename: 'upload.jpg'),
      );
    } else if (_image != null) {
      request.files.add(
        await http.MultipartFile.fromPath('file', _image!.path),
      );
    }
    var response = await request.send();
    if (response.statusCode == 200) {
      var respStr = await response.stream.bytesToString();
      var data = json.decode(respStr);
      setState(() {
        _ocrResult = (data['results'] as List)
            .map<String>((r) => 'Texto: ${r['text']} | Confiança: ${r['conf']}')
            .join('\n');
      });
    } else {
      setState(() {
        _ocrResult = "Erro ao processar imagem";
      });
    }
    setState(() { _isSending = false; });
  }

  @override
  Widget build(BuildContext context) {
    Widget imageWidget;
    if (_image != null) {
      imageWidget = Image.file(_image!);
    } else if (_webImage != null) {
      imageWidget = Image.memory(_webImage!);
    } else {
      imageWidget = const Placeholder(fallbackHeight: 200);
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Placa OCR')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            imageWidget,
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ElevatedButton(
                  onPressed: _pickImage,
                  child: const Text('Tirar Foto'),
                ),
                const SizedBox(width: 20),
                ElevatedButton(
                  onPressed: ((_image != null || _webImage != null) && !_isSending) ? _sendToBackend : null,
                  child: _isSending ? const CircularProgressIndicator() : const Text('Enviar'),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(_ocrResult),
          ],
        ),
      ),
    );
  }
}
