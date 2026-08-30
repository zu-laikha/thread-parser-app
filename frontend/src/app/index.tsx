import * as Clipboard from 'expo-clipboard';
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useTheme } from '@/hooks/use-theme';

type ParsedPost = {
  category: string;
  subcategory: string;
  title: string;
  brand_or_creator: string;
  location: string;
  dates_or_validity: string;
  key_highlights: string[];
  original_url: string;
  image_url?: string;
  image_urls?: string[];
};

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

export default function HomeScreen() {
  const theme = useTheme();
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<ParsedPost | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function pasteUrl() {
    setUrl(await Clipboard.getStringAsync());
  }

  async function parsePost() {
    const trimmedUrl = url.trim();
    if (!/^https?:\/\/(www\.)?(threads\.net|threads\.com)\//i.test(trimmedUrl)) {
      setError('Enter a valid Threads post URL.');
      setResult(null);
      return;
    }

    setIsLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmedUrl }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to parse this post.');
      }
      setResult(payload as ParsedPost);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to reach the parser.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.heading}>
          <ThemedText type="smallBold" themeColor="textSecondary">THREAD LINK SUMMARIZER</ThemedText>
          <ThemedText type="title" style={styles.title}>Make the thread useful.</ThemedText>
          <ThemedText themeColor="textSecondary">Turn a Threads post into a clear, saveable summary.</ThemedText>
        </View>

        <ThemedView type="backgroundElement" style={styles.inputPanel}>
          <ThemedText type="smallBold">Threads post URL</ThemedText>
          <TextInput
            value={url}
            onChangeText={setUrl}
            placeholder="https://www.threads.net/..."
            placeholderTextColor={theme.textSecondary}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            style={[styles.input, { color: theme.text, borderColor: theme.textSecondary }]}
          />
          <View style={styles.actions}>
            <Pressable onPress={pasteUrl} style={[styles.secondaryButton, { borderColor: theme.textSecondary }]}>
              <ThemedText type="smallBold">Paste</ThemedText>
            </Pressable>
            <Pressable disabled={isLoading} onPress={parsePost} style={styles.primaryButton}>
              {isLoading ? <ActivityIndicator color="#ffffff" /> : <ThemedText type="smallBold" style={styles.buttonText}>Analyze</ThemedText>}
            </Pressable>
          </View>
        </ThemedView>

        {!!error && <ThemedText style={styles.error}>{error}</ThemedText>}

        {result && (
          <ThemedView type="backgroundElement" style={styles.resultCard}>
            {(result.image_urls && result.image_urls.length > 0) ? (
              <ScrollView
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.carouselContainer}
              >
                {result.image_urls.map((imageUrl, index) => (
                  <View key={`${imageUrl}-${index}`} style={styles.carouselItem}>
                    <Image
                      source={{ uri: imageUrl }}
                      style={styles.resultImage}
                      resizeMode="cover"
                    />
                  </View>
                ))}
              </ScrollView>
            ) : result.image_url ? (
              <ScrollView
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.carouselContainer}
              >
                <View style={styles.carouselItem}>
                  <Image
                    source={{ uri: result.image_url }}
                    style={styles.resultImage}
                    resizeMode="cover"
                  />
                </View>
              </ScrollView>
            ) : null}
            <View style={styles.resultHeader}>
              <ThemedText type="smallBold" themeColor="textSecondary">{result.category.toUpperCase()}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">{result.subcategory}</ThemedText>
            </View>
            <ThemedText type="subtitle" style={styles.resultTitle}>{result.title}</ThemedText>
            <InfoRow label="Creator / brand" value={result.brand_or_creator} />
            <InfoRow label="Location" value={result.location} />
            <InfoRow label="When / validity" value={result.dates_or_validity} />
            <ThemedText type="smallBold" style={styles.highlightsLabel}>Highlights</ThemedText>
            {result.key_highlights.map((highlight, index) => <ThemedText key={`${highlight}-${index}`} themeColor="textSecondary">• {highlight}</ThemedText>)}
            <Pressable onPress={() => Linking.openURL(result.original_url)}>
              <ThemedText type="linkPrimary" style={styles.sourceLink}>Open original post</ThemedText>
            </Pressable>
          </ThemedView>
        )}
      </SafeAreaView>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <ThemedText type="smallBold">{label}</ThemedText>
      <ThemedText themeColor="textSecondary">{value}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    paddingHorizontal: 20,
  },
  safeArea: {
    flex: 1,
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    paddingVertical: 32,
  },
  heading: {
    marginBottom: 28,
  },
  title: {
    fontSize: 42,
    lineHeight: 46,
  },
  inputPanel: {
    padding: 20,
    borderRadius: 12,
  },
  input: {
    minHeight: 52,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 14,
    fontSize: 16,
  },
  actions: {
    flexDirection: 'row',
  },
  primaryButton: {
    flex: 1,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    backgroundColor: '#147D92',
  },
  secondaryButton: {
    minHeight: 48,
    paddingHorizontal: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    borderWidth: 1,
  },
  buttonText: {
    color: '#ffffff',
  },
  error: {
    color: '#C24135',
    marginTop: 16,
  },
  resultCard: {
    marginTop: 24,
    padding: 22,
    borderRadius: 12,
  },
  carouselContainer: {
    paddingRight: 8,
  },
  carouselItem: {
    width: 300,
    marginRight: 12,
  },
  resultImage: {
    width: '100%',
    height: 240,
    borderRadius: 10,
    backgroundColor: '#dfe8ea',
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  resultTitle: {
    fontSize: 28,
    lineHeight: 34,
    marginBottom: 8,
  },
  infoRow: {
    marginTop: 6,
  },
  highlightsLabel: {
    marginTop: 14,
  },
  sourceLink: {
    marginTop: 14,
  },
});
