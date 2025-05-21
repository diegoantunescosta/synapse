import 'dart:io';
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
  String _ocrResult = "";

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.camera);
    if (pickedFile != null) {
      setState(() {
        _image = File(pickedFile.path);
        _ocrResult = "";
      });
      await _sendToBackend(_image!);
    }
  }

  Future<void> _sendToBackend(File image) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('http://SEU_IP:8000/detect-ocr/'), // Troque SEU_IP pelo IP do backend
    );
    request.files.add(await http.MultipartFile.fromPath('file', image.path));
    var response = await request.send();
    if (response.statusCode == 200) {
      var respStr = await response.stream.bytesToString();
      var data = json.decode(respStr);
      setState(() {
        _ocrResult = (data['results'] as List)
            .map<String>((r) => 'Texto: [1m${r['text']}[0m | Confiança: ${r['conf']}')
            .join('\n');
      });
    } else {
      setState(() {
        _ocrResult = "Erro ao processar imagem";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Placa OCR')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            _image != null
                ? Image.file(_image!)
                : const Placeholder(fallbackHeight: 200),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _pickImage,
              child: const Text('Tirar Foto'),
            ),
            const SizedBox(height: 20),
            Text(_ocrResult),
          ],
        ),
      ),
    );
  }
}
