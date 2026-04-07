import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class MaarifXClient {
  final String apiKey;
  final String baseUrl;
  final String? subUserToken;

  MaarifXClient({
    required this.apiKey,
    this.baseUrl = 'https://api2.ogretimsayfam.com',
    this.subUserToken,
  });

  Map<String, String> get _headers => {
        'X-API-Key': apiKey,
        if (subUserToken != null) 'X-Sub-User-Token': subUserToken!,
      };

  /// Solve a question (synchronous mode - waits for full result).
  Future<SolveResult> solve({
    required File image,
    String? text,
    bool drawOnImage = false,
    int? detailLevel,
    String? classLevel,
    String? userToken,
  }) async {
    if (drawOnImage && (classLevel == null || !['7', '8', '9', '10', '11'].contains(classLevel))) {
      throw MaarifXException('classLevel (7-11) is required when drawOnImage=true', 400);
    }
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/v1/solve'));
    request.headers.addAll(_headers);
    if (userToken != null) request.headers['X-Sub-User-Token'] = userToken;

    request.files.add(await http.MultipartFile.fromPath('image', image.path));
    request.fields['stream'] = 'false';
    request.fields['draw_on_image'] = drawOnImage.toString();
    if (classLevel != null) request.fields['classLevel'] = classLevel;
    if (text != null) request.fields['text'] = text;
    if (detailLevel != null) request.fields['detailLevel'] = detailLevel.toString();

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      throw MaarifXException(body['error'] ?? 'Unknown error', response.statusCode);
    }

    return SolveResult.fromJson(jsonDecode(response.body));
  }

  /// Solve a question with SSE streaming - yields events as they arrive.
  Stream<SSEEvent> solveStream({
    required File image,
    String? text,
    bool drawOnImage = false,
    int? detailLevel,
    String? classLevel,
    String? userToken,
  }) async* {
    if (drawOnImage && (classLevel == null || !['7', '8', '9', '10', '11'].contains(classLevel))) {
      throw MaarifXException('classLevel (7-11) is required when drawOnImage=true', 400);
    }
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/v1/solve'));
    request.headers.addAll(_headers);
    if (userToken != null) request.headers['X-Sub-User-Token'] = userToken;

    request.files.add(await http.MultipartFile.fromPath('image', image.path));
    request.fields['stream'] = 'true';
    request.fields['draw_on_image'] = drawOnImage.toString();
    if (classLevel != null) request.fields['classLevel'] = classLevel;
    if (text != null) request.fields['text'] = text;
    if (detailLevel != null) request.fields['detailLevel'] = detailLevel.toString();

    final streamedResponse = await request.send();

    if (streamedResponse.statusCode != 200) {
      final body = await streamedResponse.stream.bytesToString();
      final parsed = jsonDecode(body);
      throw MaarifXException(parsed['error'] ?? 'Unknown error', streamedResponse.statusCode);
    }

    String buffer = '';
    String currentEvent = '';

    await for (final chunk in streamedResponse.stream.transform(utf8.decoder)) {
      buffer += chunk;
      final lines = buffer.split('\n');
      buffer = lines.removeLast();

      for (final line in lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          final dataStr = line.substring(5).trim();
          try {
            final data = jsonDecode(dataStr);
            yield SSEEvent(type: currentEvent, data: data);
          } catch (_) {}
        }
      }
    }
  }

  /// Register a sub-user (auth-based API keys only).
  Future<SubUser> registerUser({
    required String externalId,
    String? displayName,
    String? email,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/v1/users/register'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode({
        'external_id': externalId,
        if (displayName != null) 'display_name': displayName,
        if (email != null) 'email': email,
      }),
    );

    if (response.statusCode != 201) {
      final body = jsonDecode(response.body);
      throw MaarifXException(body['error'] ?? 'Registration failed', response.statusCode);
    }

    return SubUser.fromJson(jsonDecode(response.body));
  }

  /// Verify a sub-user token.
  Future<Map<String, dynamic>> verifyUser(String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/v1/users/verify'),
      headers: {..._headers, 'Content-Type': 'application/json'},
      body: jsonEncode({'token': token}),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      throw MaarifXException(body['error'] ?? 'Verification failed', response.statusCode);
    }

    return jsonDecode(response.body);
  }

  /// Get usage statistics.
  Future<Map<String, dynamic>> getUsage() async {
    final response = await http.get(
      Uri.parse('$baseUrl/v1/usage'),
      headers: _headers,
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      throw MaarifXException(body['error'] ?? 'Failed to get usage', response.statusCode);
    }

    return jsonDecode(response.body);
  }
}

class SolveResult {
  final String requestId;
  final String status;
  final String? text;
  final String? viewUrl;
  final int inputTokens;
  final int outputTokens;

  SolveResult({
    required this.requestId,
    required this.status,
    this.text,
    this.viewUrl,
    required this.inputTokens,
    required this.outputTokens,
  });

  factory SolveResult.fromJson(Map<String, dynamic> json) {
    return SolveResult(
      requestId: json['requestId'] ?? '',
      status: json['status'] ?? 'completed',
      text: json['text'],
      viewUrl: json['view_url'],
      inputTokens: json['usage']?['input_tokens'] ?? 0,
      outputTokens: json['usage']?['output_tokens'] ?? 0,
    );
  }
}

class SSEEvent {
  final String type;
  final Map<String, dynamic> data;

  SSEEvent({required this.type, required this.data});

  String? get token => data['token'] as String?;
  String? get message => data['message'] as String?;
  String? get requestId => data['requestId'] as String?;
  String? get viewUrl => data['view_url'] as String?;
  Map<String, dynamic>? get usage => data['usage'] as Map<String, dynamic>?;
}

class SubUser {
  final String subUserId;
  final String token;
  final int dailyLimit;

  SubUser({
    required this.subUserId,
    required this.token,
    required this.dailyLimit,
  });

  factory SubUser.fromJson(Map<String, dynamic> json) {
    return SubUser(
      subUserId: json['sub_user_id'] ?? '',
      token: json['token'] ?? '',
      dailyLimit: json['daily_limit'] ?? 0,
    );
  }
}

class MaarifXException implements Exception {
  final String message;
  final int statusCode;

  MaarifXException(this.message, this.statusCode);

  @override
  String toString() => 'MaarifXException($statusCode): $message';
}
