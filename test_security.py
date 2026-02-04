"""
Security Tests

Tests for security features:
- CSRF protection
- Rate limiting
- Input sanitization
- Abuse detection
"""

import unittest
from datetime import datetime, timedelta

from app.security import (
    sanitize_string, sanitize_payload, AbuseDetector,
    generate_csrf_token, validate_csrf_token
)


class TestInputSanitization(unittest.TestCase):
    """Test input sanitization functions."""
    
    def test_sanitize_string_removes_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        # Test HTML/script injection
        dangerous = '<script>alert("xss")</script>'
        sanitized = sanitize_string(dangerous)
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
    
    def test_sanitize_string_preserves_safe_text(self):
        """Test that safe text is preserved."""
        safe = 'John O\'Connor-Smith'
        sanitized = sanitize_string(safe)
        self.assertEqual(sanitized, safe)
    
    def test_sanitize_string_handles_unicode(self):
        """Test handling of unicode characters."""
        unicode_text = 'José García-Müller'
        sanitized = sanitize_string(unicode_text)
        self.assertEqual(sanitized, unicode_text)
    
    def test_sanitize_string_trims_whitespace(self):
        """Test that whitespace is trimmed."""
        text = '  John Smith  '
        sanitized = sanitize_string(text)
        self.assertEqual(sanitized, 'John Smith')
    
    def test_sanitize_string_empty_input(self):
        """Test handling of empty input."""
        self.assertEqual(sanitize_string(''), '')
        self.assertEqual(sanitize_string(None), '')
    
    def test_sanitize_payload_nested_dict(self):
        """Test sanitization of nested dictionaries."""
        payload = {
            'name': '<script>alert(1)</script>John',
            'address': {
                'street': '123 <b>Test</b> Street',
                'city': 'Brisbane'
            },
            'items': [
                {'name': '<img src=x onerror=alert(1)>'},
                'safe string'
            ]
        }
        
        sanitized = sanitize_payload(payload)
        
        # Check dangerous content removed
        self.assertNotIn('<', sanitized['name'])
        self.assertNotIn('<', sanitized['address']['street'])
        self.assertNotIn('<', sanitized['items'][0]['name'])
        
        # Check safe content preserved
        self.assertEqual(sanitized['address']['city'], 'Brisbane')
        self.assertEqual(sanitized['items'][1], 'safe string')
    
    def test_sanitize_payload_preserves_types(self):
        """Test that non-string types are preserved."""
        payload = {
            'string': 'test',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'null': None,
            'list': [1, 2, 3]
        }
        
        sanitized = sanitize_payload(payload)
        
        self.assertEqual(sanitized['string'], 'test')
        self.assertEqual(sanitized['integer'], 42)
        self.assertEqual(sanitized['float'], 3.14)
        self.assertEqual(sanitized['boolean'], True)
        self.assertIsNone(sanitized['null'])
        self.assertEqual(sanitized['list'], [1, 2, 3])


class TestAbuseDetector(unittest.TestCase):
    """Test abuse detection functionality."""
    
    def setUp(self):
        """Set up abuse detector."""
        self.detector = AbuseDetector()
        self.test_ip = '192.168.1.1'
    
    def test_record_request_tracks_count(self):
        """Test that requests are tracked."""
        # Record multiple requests
        for _ in range(5):
            self.detector.record_request(self.test_ip)
        
        # Check count
        count = self.detector.get_request_count(self.test_ip)
        self.assertEqual(count, 5)
    
    def test_is_blocked_after_excessive_requests(self):
        """Test blocking after excessive requests."""
        # Should not be blocked initially
        self.assertFalse(self.detector.is_blocked(self.test_ip))
        
        # Record many requests
        for _ in range(150):  # Exceeds default threshold
            self.detector.record_request(self.test_ip)
        
        # Should now be blocked
        self.assertTrue(self.detector.is_blocked(self.test_ip))
    
    def test_block_expires_after_timeout(self):
        """Test that blocks expire after timeout."""
        # Manually set block with past expiry
        past_time = datetime.utcnow() - timedelta(hours=2)
        self.detector._blocked_ips[self.test_ip] = past_time
        
        # Should not be blocked anymore
        self.assertFalse(self.detector.is_blocked(self.test_ip))
    
    def test_different_ips_tracked_separately(self):
        """Test that different IPs are tracked separately."""
        ip1 = '192.168.1.1'
        ip2 = '192.168.1.2'
        
        # Record requests for each IP
        for _ in range(10):
            self.detector.record_request(ip1)
        
        for _ in range(5):
            self.detector.record_request(ip2)
        
        # Check counts are separate
        self.assertEqual(self.detector.get_request_count(ip1), 10)
        self.assertEqual(self.detector.get_request_count(ip2), 5)
    
    def test_cleanup_old_requests(self):
        """Test cleanup of old request records."""
        # Record some requests
        for _ in range(10):
            self.detector.record_request(self.test_ip)
        
        # Manually age the records
        old_time = datetime.utcnow() - timedelta(hours=2)
        if self.test_ip in self.detector._requests:
            for req in self.detector._requests[self.test_ip]:
                req['timestamp'] = old_time
        
        # Cleanup should remove old requests
        self.detector.cleanup_old_requests()
        
        # Count should be reset
        count = self.detector.get_request_count(self.test_ip)
        self.assertEqual(count, 0)


class TestCSRFProtection(unittest.TestCase):
    """Test CSRF token generation and validation."""
    
    def test_generate_csrf_token_returns_string(self):
        """Test that token generation returns a string."""
        token = generate_csrf_token()
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
    
    def test_generate_csrf_token_unique(self):
        """Test that tokens are unique."""
        tokens = [generate_csrf_token() for _ in range(10)]
        self.assertEqual(len(set(tokens)), 10, "Tokens should be unique")
    
    def test_validate_csrf_token_valid(self):
        """Test validation of valid token."""
        token = generate_csrf_token()
        is_valid = validate_csrf_token(token, token)
        self.assertTrue(is_valid)
    
    def test_validate_csrf_token_invalid(self):
        """Test validation of invalid token."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        is_valid = validate_csrf_token(token1, token2)
        self.assertFalse(is_valid)
    
    def test_validate_csrf_token_empty(self):
        """Test validation with empty token."""
        is_valid = validate_csrf_token('', 'token')
        self.assertFalse(is_valid)
        
        is_valid = validate_csrf_token('token', '')
        self.assertFalse(is_valid)
    
    def test_validate_csrf_token_none(self):
        """Test validation with None token."""
        is_valid = validate_csrf_token(None, 'token')
        self.assertFalse(is_valid)


class TestSecurityEdgeCases(unittest.TestCase):
    """Test security edge cases."""
    
    def test_sanitize_very_long_string(self):
        """Test sanitization of very long strings."""
        long_string = 'A' * 10000
        sanitized = sanitize_string(long_string)
        self.assertEqual(len(sanitized), 10000)
    
    def test_sanitize_nested_deeply(self):
        """Test sanitization of deeply nested structures."""
        payload = {'level1': {'level2': {'level3': {'level4': '<script>test</script>'}}}}
        sanitized = sanitize_payload(payload)
        self.assertNotIn('<', sanitized['level1']['level2']['level3']['level4'])
    
    def test_abuse_detector_different_thresholds(self):
        """Test abuse detector with different thresholds."""
        detector = AbuseDetector(request_threshold=5, block_duration_minutes=1)
        
        # Should not be blocked after 4 requests
        for _ in range(4):
            detector.record_request('test_ip')
        self.assertFalse(detector.is_blocked('test_ip'))
        
        # One more request should trigger block
        detector.record_request('test_ip')
        self.assertTrue(detector.is_blocked('test_ip'))


if __name__ == '__main__':
    unittest.main()
