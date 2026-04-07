import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'maarifx_client.dart';

void main() => runApp(const MaarifXDemoApp());

class MaarifXDemoApp extends StatelessWidget {
  const MaarifXDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MaarifX API Demo',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6366F1),
          brightness: Brightness.dark,
        ),
      ),
      home: const SolvePage(),
    );
  }
}

class SolvePage extends StatefulWidget {
  const SolvePage({super.key});

  @override
  State<SolvePage> createState() => _SolvePageState();
}

class _SolvePageState extends State<SolvePage> {
  final _apiKeyController = TextEditingController();
  final _textController = TextEditingController();
  final _picker = ImagePicker();

  File? _selectedImage;
  bool _drawOnImage = false;
  String _classLevel = '9';
  bool _isLoading = false;
  String _status = '';
  String _outputText = '';
  String _thinkingText = '';
  String? _viewUrl;
  int _inputTokens = 0;
  int _outputTokens = 0;

  Future<void> _pickImage() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 2048);
    if (picked != null) {
      setState(() => _selectedImage = File(picked.path));
    }
  }

  Future<void> _solve() async {
    if (_apiKeyController.text.isEmpty || _selectedImage == null) return;

    setState(() {
      _isLoading = true;
      _status = 'Connecting...';
      _outputText = '';
      _thinkingText = '';
      _viewUrl = null;
      _inputTokens = 0;
      _outputTokens = 0;
    });

    final client = MaarifXClient(apiKey: _apiKeyController.text.trim());

    try {
      await for (final event in client.solveStream(
        image: _selectedImage!,
        text: _textController.text.isNotEmpty ? _textController.text : null,
        drawOnImage: _drawOnImage,
        classLevel: _classLevel,
      )) {
        if (!mounted) return;

        setState(() {
          switch (event.type) {
            case 'accepted':
              _status = 'Processing...';
              break;
            case 'status':
              _status = event.message ?? 'Processing...';
              break;
            case 'thinking':
              _thinkingText += event.token ?? '';
              break;
            case 'thinking_done':
              _status = 'Solving...';
              break;
            case 'token':
              _outputText += event.token ?? '';
              break;
            case 'complete':
              _status = 'Completed';
              _isLoading = false;
              _viewUrl = event.viewUrl;
              _inputTokens = event.usage?['input_tokens'] ?? 0;
              _outputTokens = event.usage?['output_tokens'] ?? 0;
              if (event.data['text'] != null) {
                _outputText = event.data['text'];
              }
              break;
            case 'error':
              _status = 'Error: ${event.message}';
              _isLoading = false;
              break;
          }
        });
      }
    } on MaarifXException catch (e) {
      if (mounted) {
        setState(() {
          _status = 'Error: ${e.message}';
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = 'Error: $e';
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MaarifX API Demo')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _apiKeyController,
              decoration: const InputDecoration(
                labelText: 'API Key',
                hintText: 'mfx_req_... or mfx_auth_...',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),

            GestureDetector(
              onTap: _pickImage,
              child: Container(
                height: 200,
                decoration: BoxDecoration(
                  border: Border.all(
                    color: _selectedImage != null ? Colors.green : Colors.grey,
                    width: 2,
                    strokeAlign: BorderSide.strokeAlignInside,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: _selectedImage != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: Image.file(_selectedImage!, fit: BoxFit.contain),
                      )
                    : const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.add_photo_alternate, size: 48, color: Colors.grey),
                            SizedBox(height: 8),
                            Text('Tap to select an image', style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 16),

            TextField(
              controller: _textController,
              decoration: const InputDecoration(
                labelText: 'Additional text (optional)',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 12),

            DropdownButtonFormField<String>(
              value: _classLevel,
              decoration: const InputDecoration(
                labelText: 'Class Level',
                border: OutlineInputBorder(),
              ),
              items: ['7', '8', '9', '10', '11']
                  .map((v) => DropdownMenuItem(value: v, child: Text('$v. Sinif')))
                  .toList(),
              onChanged: (v) => setState(() => _classLevel = v!),
            ),
            const SizedBox(height: 12),

            SwitchListTile(
              title: const Text('Draw on image'),
              value: _drawOnImage,
              onChanged: (v) => setState(() => _drawOnImage = v),
            ),
            const SizedBox(height: 16),

            FilledButton.icon(
              onPressed: _isLoading || _selectedImage == null || _apiKeyController.text.isEmpty
                  ? null
                  : _solve,
              icon: _isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.auto_fix_high),
              label: Text(_isLoading ? 'Solving...' : 'Solve'),
            ),

            if (_status.isNotEmpty) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(_status, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
              ),
            ],

            if (_thinkingText.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                constraints: const BoxConstraints(maxHeight: 150),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E1B2E),
                  border: Border.all(color: const Color(0xFF312E81)),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SingleChildScrollView(
                  child: Text(
                    _thinkingText,
                    style: const TextStyle(fontSize: 12, color: Color(0xFFA5B4FC)),
                  ),
                ),
              ),
            ],

            if (_viewUrl != null && _drawOnImage) ...[
              const SizedBox(height: 16),
              SizedBox(
                height: 500,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: WebViewWidget(
                    controller: WebViewController()
                      ..setJavaScriptMode(JavaScriptMode.unrestricted)
                      ..loadRequest(Uri.parse(_viewUrl!)),
                  ),
                ),
              ),
            ] else if (_outputText.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                constraints: const BoxConstraints(maxHeight: 400),
                decoration: BoxDecoration(
                  color: Colors.black,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SingleChildScrollView(
                  child: SelectableText(
                    _outputText,
                    style: const TextStyle(fontSize: 14, height: 1.6),
                  ),
                ),
              ),
            ],

            if (_inputTokens > 0 || _outputTokens > 0) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Text('Input: $_inputTokens tokens',
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(width: 16),
                  Text('Output: $_outputTokens tokens',
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
